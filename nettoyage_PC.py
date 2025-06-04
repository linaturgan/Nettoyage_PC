import os
import shutil
from pathlib import Path
import hashlib
import datetime
import tkinter as tk
from tkinter import messagebox, filedialog, ttk, scrolledtext
import subprocess
import platform
import threading

# --- Détection de l'OS ---
OS = platform.system()

# --- Journalisation ---
log_file = Path.home() / "Documents" / "nettoyage_log.txt"
log_gui_callback = None

def log(message):
    timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    line = f"{timestamp} {message}\n"
    with open(log_file, "a") as f:
        f.write(line)
    if log_gui_callback:
        log_gui_callback(line)

# --- Statistiques ---
statistiques = {"supprimes": 0, "erreurs": 0, "simules": 0, "taille_totale": 0}

# --- Pré-scan pour calculer le total de fichiers à traiter ---
def compter_fichiers(dossiers, extensions_cibles):
    total = 0
    for dossier in dossiers:
        dossier_path = Path(dossier).expanduser()
        if not dossier_path.exists():
            continue
        for root, dirs, files in os.walk(dossier_path):
            for name in files:
                file_path = Path(root) / name
                if extensions_cibles is None or file_path.suffix in extensions_cibles:
                    total += 1
    return total

# --- Suppression ciblée ---
def supprimer(item, simulate):
    try:
        taille = item.stat().st_size
    except:
        taille = 0

    if simulate:
        msg = f"[SIMULATION] ⚠️ A supprimer : {item}"
        statistiques["simules"] += 1
        statistiques["taille_totale"] += taille
        log(msg)
        return msg
    else:
        try:
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
            statistiques["supprimes"] += 1
            statistiques["taille_totale"] += taille
            msg = f"✅ Supprimé : {item}"
            log(msg)
            return msg
        except Exception as e:
            statistiques["erreurs"] += 1
            msg = f"❌ Erreur suppression {item}: {e}"
            log(msg)
            return msg

def nettoyer_dossier(dossier, extensions_cibles=None, simulate=True, file_callback=None, message_callback=None, progress_callback=None, compteur=[0], total=1):
    dossier_path = Path(dossier).expanduser()
    if not dossier_path.exists():
        return
    for root, dirs, files in os.walk(dossier_path):
        for name in files:
            file_path = Path(root) / name
            if extensions_cibles is None or file_path.suffix in extensions_cibles:
                if file_callback:
                    file_callback(file_path)
                msg = supprimer(file_path, simulate)
                if message_callback:
                    message_callback(msg)
                compteur[0] += 1
                if progress_callback and total > 0:
                    progress_callback(compteur[0] / total)

def action_nettoyer(simulate, progress_callback=None, status_callback=None, file_callback=None, message_callback=None):
    global statistiques
    statistiques = {"supprimes": 0, "erreurs": 0, "simules": 0, "taille_totale": 0}

    extensions = ['.log', '.tmp']
    if OS == "Darwin":
        extensions.append('.DS_Store')

    log("--- Début du nettoyage ---")

    dossiers = [Path.home() / "Downloads", Path.home() / "Documents"]
    if OS == "Darwin":
        dossiers.append(Path.home() / "Library" / "Caches")
    elif OS == "Windows":
        dossiers.append(Path.home() / "AppData" / "Local" / "Temp")

    if status_callback:
        status_callback("Calcul du nombre de fichiers...")
    total_fichiers = compter_fichiers(dossiers, extensions)

    if total_fichiers == 0:
        log("Aucun fichier à traiter.")
        if status_callback:
            status_callback("Aucun fichier à nettoyer ✅")
        messagebox.showinfo("Nettoyage terminé", "Aucun fichier à nettoyer.")
        return

    compteur = [0]

    if status_callback:
        status_callback("Nettoyage en cours...")

    for dossier in dossiers:
        nettoyer_dossier(
            dossier,
            extensions if dossier in [Path.home() / "Downloads", Path.home() / "Documents"] else None,
            simulate, file_callback, message_callback, progress_callback, compteur, total_fichiers
        )

    taille_mo = statistiques['taille_totale'] / (1024 * 1024)
    log(f"Fichiers supprimés : {statistiques['supprimes']}")
    log(f"Fichiers simulés : {statistiques['simules']}")
    log(f"Erreurs rencontrées : {statistiques['erreurs']}")
    log(f"Taille totale ciblée : {taille_mo:.2f} Mo")
    log("--- Fin du nettoyage ---\n")

    if status_callback:
        status_callback("Nettoyage terminé ✅")

    messagebox.showinfo("Nettoyage terminé", f"Nettoyage terminé ✅\n\nSupprimés : {statistiques['supprimes']}\nSimulés : {statistiques['simules']}\nErreurs : {statistiques['erreurs']}\nTaille totale : {taille_mo:.2f} Mo")

# --- GUI ---
def lancer_gui():
    global log_gui_callback

    root = tk.Tk()
    root.title("🧹 Nettoyeur Universel PRO")
    root.geometry("700x600")
    root.configure(bg="white")

    simulation_var = tk.BooleanVar(value=True)

    tk.Label(root, text="Nettoyage de fichiers inutiles", font=("Arial", 14), bg="white").pack(pady=10)
    tk.Checkbutton(root, text="Mode simulation (ne rien supprimer)", variable=simulation_var, bg="white").pack()

    progress = ttk.Progressbar(root, length=600, mode="determinate")
    progress.pack(pady=5)

    status_label = tk.Label(root, text="", font=("Arial", 10), bg="white")
    status_label.pack(pady=5)

    current_file_label = tk.Label(root, text="", font=("Arial", 8), bg="white", wraplength=680, justify="left")
    current_file_label.pack(pady=5)

    message_label = tk.Label(root, text="", font=("Arial", 9), bg="white", fg="red", wraplength=680, justify="left")
    message_label.pack(pady=5)

    log_frame = tk.LabelFrame(root, text="Journal temps réel", bg="white", padx=5, pady=5)
    log_frame.pack(fill="both", expand=True, padx=10, pady=10)

    log_text = scrolledtext.ScrolledText(log_frame, state="disabled", height=15, wrap="word")
    log_text.pack(fill="both", expand=True)

    def update_progress(value):
        progress["value"] = value * 100
        root.update_idletasks()

    def update_status(text):
        status_label.config(text=text)
        root.update_idletasks()

    def update_current_file(path):
        current_file_label.config(text=str(path))
        root.update_idletasks()

    def update_message(msg):
        message_label.config(text=msg)
        root.update_idletasks()

    def update_log_gui(line):
        log_text.configure(state="normal")
        log_text.insert("end", line)
        log_text.see("end")
        log_text.configure(state="disabled")

    log_gui_callback = update_log_gui

    def lancer_nettoyage_thread():
        threading.Thread(
            target=action_nettoyer,
            args=(simulation_var.get(), update_progress, update_status, update_current_file, update_message),
            daemon=True
        ).start()

    tk.Button(root, text="🧹 Lancer le nettoyage", command=lancer_nettoyage_thread).pack(pady=10)
    tk.Button(root, text="📄 Ouvrir le journal externe", command=lambda: ouvrir_journal()).pack(pady=5)
    tk.Label(root, text="v5.1 - Mac & Windows", font=("Arial", 8), bg="white").pack(side="bottom", pady=10)

    root.mainloop()

def ouvrir_journal():
    try:
        if OS == "Windows":
            os.startfile(log_file)
        elif OS == "Darwin":
            subprocess.run(["open", str(log_file)])
        else:
            subprocess.run(["xdg-open", str(log_file)])
    except Exception as e:
        messagebox.showerror("Erreur", f"Impossible d'ouvrir le journal : {e}")

if __name__ == "__main__":
    lancer_gui()
