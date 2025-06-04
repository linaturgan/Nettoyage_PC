import os
import shutil
import threading
import time
import subprocess
import platform
from pathlib import Path
import datetime
import tkinter as tk
from tkinter import messagebox, filedialog, ttk, scrolledtext

# --- Détection OS ---
OS = platform.system()

# --- Log ---
log_file = Path.home() / "Documents" / "nettoyage_log.txt"
log_gui_callback = None
stop_flag = threading.Event()
fichiers_non_supprimes = []

def log(message):
    timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    line = f"{timestamp} {message}\n"
    with open(log_file, "a") as f:
        f.write(line)
    if log_gui_callback:
        log_gui_callback(line)

# --- Statistiques ---
statistiques = {"supprimes": 0, "erreurs": 0, "simules": 0, "taille_totale": 0}
timeout_suppression = 5  # secondes max par fichier

def compter_fichiers(dossiers, extensions_cibles):
    total = 0
    for dossier in dossiers:
        for root, dirs, files in os.walk(Path(dossier).expanduser()):
            for name in files:
                path = Path(root) / name
                if extensions_cibles is None or path.suffix in extensions_cibles:
                    total += 1
    return total

def suppression_reelle(path, simulate, resultat):
    try:
        taille = path.stat().st_size
    except:
        taille = 0
    if simulate:
        statistiques["simules"] += 1
        statistiques["taille_totale"] += taille
        resultat.append(f"[SIMULATION] ⚠️ A supprimer : {path}")
    else:
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            statistiques["supprimes"] += 1
            statistiques["taille_totale"] += taille
            resultat.append(f"✅ Supprimé : {path}")
        except Exception as e:
            statistiques["erreurs"] += 1
            resultat.append(f"❌ Erreur suppression {path}: {e}")

def supprimer(path, simulate):
    resultat = []
    thread = threading.Thread(target=suppression_reelle, args=(path, simulate, resultat))
    thread.start()
    thread.join(timeout_suppression)
    if thread.is_alive():
        fichiers_non_supprimes.append(path)
        resultat.append(f"⏳ Timeout suppression pour : {path}")
    return resultat[0]

def nettoyer_dossier(dossiers, extensions, simulate, progress_callback, status_callback, file_callback, message_callback, compteur, total):
    for dossier in dossiers:
        for root, dirs, files in os.walk(Path(dossier).expanduser()):
            for name in files:
                if stop_flag.is_set():
                    return
                path = Path(root) / name
                log(f"Analyse de {path}")
                if extensions is None or path.suffix in extensions:
                    msg = supprimer(path, simulate)
                    if file_callback:
                        file_callback(path)
                    if message_callback:
                        message_callback(msg)
                    compteur[0] += 1
                    if progress_callback:
                        progress_callback(compteur[0] / total)

def action_nettoyer(dossiers, extensions, simulate, progress_callback, status_callback, file_callback, message_callback, finish_callback):
    global statistiques, fichiers_non_supprimes
    statistiques = {"supprimes": 0, "erreurs": 0, "simules": 0, "taille_totale": 0}
    fichiers_non_supprimes = []
    stop_flag.clear()

    log("--- Début du nettoyage ---")
    status_callback("Calcul du nombre de fichiers...")
    total = compter_fichiers(dossiers, extensions)

    if total == 0:
        log("Aucun fichier à traiter.")
        status_callback("Aucun fichier à nettoyer ✅")
        messagebox.showinfo("Nettoyage terminé", "Aucun fichier à nettoyer.")
        finish_callback()
        return

    compteur = [0]
    status_callback("Nettoyage en cours...")
    nettoyer_dossier(dossiers, extensions, simulate, progress_callback, status_callback, file_callback, message_callback, compteur, total)

    taille_mo = statistiques["taille_totale"] / (1024 * 1024)
    log(f"Fichiers supprimés : {statistiques['supprimes']}")
    log(f"Simulés : {statistiques['simules']}")
    log(f"Erreurs : {statistiques['erreurs']}")
    log(f"Taille totale ciblée : {taille_mo:.2f} Mo")
    log("--- Fin du nettoyage ---")

    status_callback("Nettoyage terminé ✅" if not stop_flag.is_set() else "Nettoyage interrompu")

    if simulate:
        messagebox.showinfo("Simulation terminée",
            f"Mode simulation terminé ✅\n\n"
            f"Fichiers simulés : {statistiques['simules']}\n"
            f"Erreurs : {statistiques['erreurs']}\n"
            f"Taille simulée : {taille_mo:.2f} Mo")
    else:
        msg_fin = f"{'Nettoyage interrompu' if stop_flag.is_set() else 'Nettoyage terminé ✅'}\n\n" \
                  f"Supprimés : {statistiques['supprimes']}\n" \
                  f"Erreurs : {statistiques['erreurs']}\n" \
                  f"Espace libéré : {taille_mo:.2f} Mo"
        if fichiers_non_supprimes:
            msg_fin += f"\n\n{len(fichiers_non_supprimes)} fichiers non supprimés (timeout)"
        messagebox.showinfo("Nettoyage terminé", msg_fin)

        if fichiers_non_supprimes:
            fichiers_txt = "\n".join(str(p) for p in fichiers_non_supprimes)
            messagebox.showinfo("Fichiers non supprimés", f"Liste des fichiers :\n{fichiers_txt}")

    finish_callback()

# --- GUI ---
def lancer_gui():
    global log_gui_callback

    root = tk.Tk()
    root.title("🧹 Nettoyeur PRO v8.0 Timeout Edition")
    root.geometry("800x750")
    root.configure(bg="white")

    simulation_var = tk.BooleanVar(value=True)
    tk.Label(root, text="Nettoyage de fichiers inutiles", font=("Arial", 14), bg="white").pack(pady=10)
    tk.Checkbutton(root, text="Mode simulation (ne rien supprimer)", variable=simulation_var, bg="white").pack()

    progress = ttk.Progressbar(root, length=700, mode="determinate")
    progress.pack(pady=5)

    status_label = tk.Label(root, text="", font=("Arial", 10), bg="white")
    status_label.pack(pady=5)
    current_file_label = tk.Label(root, text="", font=("Arial", 8), bg="white", wraplength=700, justify="left")
    current_file_label.pack(pady=5)
    message_label = tk.Label(root, text="", font=("Arial", 9), bg="white", fg="red", wraplength=700, justify="left")
    message_label.pack(pady=5)

    log_frame = tk.LabelFrame(root, text="Journal temps réel", bg="white")
    log_frame.pack(fill="both", expand=True, padx=10, pady=10)
    log_text = scrolledtext.ScrolledText(log_frame, state="disabled", height=15, wrap="word")
    log_text.pack(fill="both", expand=True)

    stop_button = tk.Button(root, text="⛔ Arrêter le nettoyage", state="disabled")
    stop_button.pack(pady=10)

    def update_progress(val): progress["value"] = val * 100; root.update_idletasks(); time.sleep(0.001)
    def update_status(txt): status_label.config(text=txt); root.update_idletasks(); time.sleep(0.001)
    def update_current_file(path): current_file_label.config(text=str(path)); root.update_idletasks(); time.sleep(0.001)
    def update_message(msg): message_label.config(text=msg); root.update_idletasks(); time.sleep(0.001)
    def update_log_gui(line): log_text.configure(state="normal"); log_text.insert("end", line)
    log_text.configure(state="disabled"); log_text.see("end"); time.sleep(0.001)
    log_gui_callback = update_log_gui

    def on_finish(): stop_button.config(state="disabled")

    def lancer_nettoyage_thread(dossiers, extensions):
        stop_button.config(state="normal")
        threading.Thread(target=action_nettoyer,
                         args=(dossiers, extensions, simulation_var.get(),
                               update_progress, update_status, update_current_file,
                               update_message, on_finish),
                         daemon=True).start()

    def lancer_global():
        extensions = ['.log', '.tmp']
        if OS == "Darwin": extensions.append('.DS_Store')
        dossiers = [Path.home() / "Downloads", Path.home() / "Documents"]
        if OS == "Darwin": dossiers.append(Path.home() / "Library" / "Caches")
        elif OS == "Windows": dossiers.append(Path.home() / "AppData" / "Local" / "Temp")
        lancer_nettoyage_thread(dossiers, extensions)

    def lancer_choix_dossier():
        dossier = filedialog.askdirectory(title="Choisissez un dossier")
        if not dossier: return
        extensions = ['.log', '.tmp']
        if OS == "Darwin": extensions.append('.DS_Store')
        lancer_nettoyage_thread([Path(dossier)], extensions)

    stop_button.config(command=lambda: stop_flag.set())
    tk.Button(root, text="🧹 Nettoyage global", command=lancer_global).pack(pady=10)
    tk.Button(root, text="📂 Nettoyer un dossier choisi", command=lancer_choix_dossier).pack(pady=5)
    tk.Button(root, text="📄 Ouvrir le journal", command=lambda: ouvrir_journal()).pack(pady=5)

    tk.Label(root, text="v8.0 Timeout Edition - Mac & Windows", font=("Arial", 8), bg="white").pack(side="bottom", pady=10)
    root.mainloop()

def ouvrir_journal():
    try:
        if OS == "Windows": os.startfile(log_file)
        elif OS == "Darwin": subprocess.run(["open", str(log_file)])
        else: subprocess.run(["xdg-open", str(log_file)])
    except Exception as e:
        messagebox.showerror("Erreur", f"Impossible d'ouvrir le journal : {e}")

if __name__ == "__main__":
    lancer_gui()
