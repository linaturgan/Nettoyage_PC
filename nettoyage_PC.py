import os
import shutil
from pathlib import Path
import hashlib
import datetime
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import subprocess
import platform
import threading

# --- Détection de l'OS ---
OS = platform.system()

# --- Journalisation ---
log_file = Path.home() / "Documents" / "nettoyage_log.txt"

def log(message):
    timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    with open(log_file, "a") as f:
        f.write(f"{timestamp} {message}\n")

# --- Statistiques ---
statistiques = {"supprimes": 0, "erreurs": 0, "simules": 0, "taille_totale": 0}

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
        print(msg)
        log(msg)
    else:
        try:
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
            statistiques["supprimes"] += 1
            statistiques["taille_totale"] += taille
            msg = f"✅ Supprimé : {item}"
            print(msg)
            log(msg)
        except Exception as e:
            statistiques["erreurs"] += 1
            msg = f"❌ Erreur suppression {item}: {e}"
            print(msg)
            log(msg)

def nettoyer_dossier(dossier, extensions_cibles=None, simulate=True, file_callback=None):
    dossier_path = Path(dossier).expanduser()
    if not dossier_path.exists():
        return
    for root, dirs, files in os.walk(dossier_path):
        for name in files:
            file_path = Path(root) / name
            if extensions_cibles is None or file_path.suffix in extensions_cibles:
                if file_callback:
                    file_callback(file_path)
                supprimer(file_path, simulate)

def action_nettoyer(simulate, progress_callback=None, status_callback=None, file_callback=None):
    global statistiques
    statistiques = {"supprimes": 0, "erreurs": 0, "simules": 0, "taille_totale": 0}

    extensions = ['.log', '.tmp']
    if OS == "Darwin":
        extensions.append('.DS_Store')

    log("--- Début du nettoyage ---")
    total_dossiers = 3
    current = 0

    if status_callback:
        status_callback("Nettoyage en cours...")

    nettoyer_dossier(Path.home() / "Downloads", extensions, simulate, file_callback=file_callback)
    current += 1
    if progress_callback:
        progress_callback(current / total_dossiers)

    nettoyer_dossier(Path.home() / "Documents", extensions, simulate, file_callback=file_callback)
    current += 1
    if progress_callback:
        progress_callback(current / total_dossiers)

    if OS == "Darwin":
        nettoyer_dossier(Path.home() / "Library" / "Caches", None, simulate, file_callback=file_callback)
    elif OS == "Windows":
        nettoyer_dossier(Path.home() / "AppData" / "Local" / "Temp", None, simulate, file_callback=file_callback)
    current += 1
    if progress_callback:
        progress_callback(current / total_dossiers)

    taille_mo = statistiques['taille_totale'] / (1024 * 1024)
    log(f"Fichiers supprimés : {statistiques['supprimes']}")
    log(f"Fichiers simulés : {statistiques['simules']}")
    log(f"Erreurs rencontrées : {statistiques['erreurs']}")
    log(f"Taille totale ciblée : {taille_mo:.2f} Mo")
    log("--- Fin du nettoyage ---\n")

    if status_callback:
        status_callback("Nettoyage terminé ✅")

    messagebox.showinfo("Nettoyage terminé", f"Nettoyage terminé ✅\n\nSupprimés : {statistiques['supprimes']}\nSimulés : {statistiques['simules']}\nErreurs : {statistiques['erreurs']}\nTaille totale : {taille_mo:.2f} Mo")

# --- Hachage de fichiers ---
def hash_fichier(path):
    h = hashlib.md5()
    try:
        with open(path, 'rb') as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()
    except:
        return None

# --- Fenêtre de doublons ---
def afficher_doublons_a_supprimer(doublons_par_hash, simulation_globale):
    window = tk.Toplevel()
    window.title("Doublons détectés")
    window.geometry("600x400")

    canvas = tk.Canvas(window)
    frame = tk.Frame(canvas)
    scrollbar = tk.Scrollbar(window, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)

    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    canvas.create_window((0, 0), window=frame, anchor='nw')

    frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    selections = []

    for h, fichiers in doublons_par_hash.items():
        if len(fichiers) < 2:
            continue
        tk.Label(frame, text=f"Original : {fichiers[0]}", fg="blue", wraplength=580, justify="left").pack(anchor="w", pady=(10, 0))
        for f in fichiers[1:]:
            var = tk.BooleanVar()
            chk = tk.Checkbutton(frame, text=str(f), variable=var, wraplength=580, justify="left")
            chk.pack(anchor="w")
            selections.append((f, var))

    progress = ttk.Progressbar(frame, length=500, mode="determinate")
    progress.pack(pady=10)

    def supprimer_selection():
        total = sum(1 for _, var in selections if var.get())
        progress["maximum"] = total
        count = 0
        for path, var in selections:
            if var.get():
                try:
                    taille = path.stat().st_size
                    if simulation_globale.get():
                        log(f"[SIMULATION] ⚠ Doublon à supprimer : {path}")
                        statistiques["simules"] += 1
                        statistiques["taille_totale"] += taille
                    else:
                        path.unlink()
                        statistiques["supprimes"] += 1
                        statistiques["taille_totale"] += taille
                        log(f"✅ Doublon supprimé : {path}")
                except Exception as e:
                    statistiques["erreurs"] += 1
                    log(f"❌ Erreur suppression doublon : {path} → {e}")
                count += 1
                progress["value"] = count
                window.update_idletasks()
        window.destroy()
        messagebox.showinfo("Doublons", f"{count} fichiers traités.")

    tk.Button(frame, text="🗑️ Supprimer les doublons sélectionnés", command=supprimer_selection).pack(pady=15)

# --- Scanner les doublons ---
def scanner_doublons(simulation):
    dossier = filedialog.askdirectory(title="Choisir un dossier à analyser")
    if not dossier:
        return
    log(f"🔍 Scan de doublons dans : {dossier}")
    hashes = {}
    doublons = {}
    for root, dirs, files in os.walk(dossier):
        for name in files:
            path = Path(root) / name
            h = hash_fichier(path)
            if h:
                if h in hashes:
                    doublons.setdefault(h, [hashes[h]]).append(path)
                else:
                    hashes[h] = path
    if doublons:
        afficher_doublons_a_supprimer(doublons, simulation)
    else:
        messagebox.showinfo("Doublons", "Aucun doublon trouvé !")

# --- GUI ---
def lancer_gui():
    root = tk.Tk()
    root.title("🧹 Nettoyeur Universel")
    root.geometry("500x450")
    root.configure(bg="white")

    simulation_var = tk.BooleanVar(value=True)

    tk.Label(root, text="Nettoyage de fichiers inutiles", font=("Arial", 14), bg="white").pack(pady=10)
    tk.Checkbutton(root, text="Mode simulation (ne rien supprimer)", variable=simulation_var, bg="white").pack()

    progress = ttk.Progressbar(root, length=400, mode="determinate")
    progress.pack(pady=5)

    status_label = tk.Label(root, text="", font=("Arial", 10), bg="white")
    status_label.pack(pady=5)

    current_file_label = tk.Label(root, text="", font=("Arial", 8), bg="white", wraplength=480, justify="left")
    current_file_label.pack(pady=5)

    def update_progress(value):
        progress["value"] = value * 100
        root.update_idletasks()

    def update_status(text):
        status_label.config(text=text)
        root.update_idletasks()

    def update_current_file(path):
        current_file_label.config(text=str(path))
        root.update_idletasks()

    def lancer_nettoyage_thread():
        threading.Thread(
            target=action_nettoyer,
            args=(simulation_var.get(), update_progress, update_status, update_current_file),
            daemon=True
        ).start()

    tk.Button(root, text="🧹 Lancer le nettoyage", command=lancer_nettoyage_thread).pack(pady=10)
    tk.Button(root, text="🔍 Scanner les doublons", command=lambda: scanner_doublons(simulation_var)).pack()
    tk.Button(root, text="📄 Ouvrir le journal", command=lambda: ouvrir_journal()).pack(pady=10)

    tk.Label(root, text="v3.2 - Mac & Windows", font=("Arial", 8), bg="white").pack(side="bottom", pady=10)

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
