import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
import threading
import webbrowser
import urllib.parse
import urllib.request
import json
import re
import os
import time
import ctypes
import difflib
import sys
import subprocess
import shutil  # <- IMPORTANTE: Añadido para poder mover los archivos viejos
from PIL import Image, ImageTk 

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# --- CONFIGURACIÓN DE AUTO-UPDATE ---
REPO_OWNER = "Juankrom17"  
REPO_NAME = "Pokemon_Finder_Deluxe_Edition"    
# ------------------------------------

try:
    from PIL import Image, ImageTk, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False

try:
    import pytesseract
    
    if getattr(sys, 'frozen', False):
        app_path = os.path.dirname(sys.executable)
    else:
        app_path = os.path.dirname(os.path.abspath(__file__))
        
    tesseract_local = os.path.join(app_path, "Tesseract-OCR", "tesseract.exe")

    possible_paths = [
        tesseract_local,
        r"D:\user\tesseract\tesseract.exe",
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    
    TESSERACT_AVAILABLE = False
    for path in possible_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            TESSERACT_AVAILABLE = True
            break
except ImportError:
    TESSERACT_AVAILABLE = False

user32 = ctypes.windll.user32

class PokemonFinderNLP:
    def __init__(self):
        self.root = tk.Tk()
        
        try:
            myappid = 'juankrom.pokefinder.deluxe.1.0' 
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
            old_exe = exe_path + ".old"
            if os.path.exists(old_exe):
                try:
                    os.remove(old_exe)
                except Exception:
                    pass

        cached_title = "Pokefinder" 
        self.root.title(cached_title) 
        self.root.geometry("440x730")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a2e")
        self.root.attributes("-topmost", True)
        # Botón para abrir la tabla de tipos
        # --- CONFIGURAR DIRECTORIO DE GUARDADO ---
        self._setup_save_directory()
        # -----------------------------------------
        
        try:
            ruta_icono = resource_path("icono.ico")
            imagen_icono = Image.open(ruta_icono)
            self.icon_img_window = ImageTk.PhotoImage(imagen_icono)
            self.root.iconphoto(True, self.icon_img_window) 
        except Exception:
            try:
                self.root.iconbitmap(resource_path("icono.ico"))
            except Exception:
                pass

        self.zones = {} 
        self.known_pokemon = set()
        self.pokemon_ids = {} 
        
        self.custom_mappings = {}
        self.custom_fixes = self._load_custom_fixes() 
        self.is_capturing = False
        
        self.overlay = None
        self.start_x = self.start_y = 0
        self.tk_preview = None
        self.f8_pressed = False
        
        self.last_raw_clean = ""
        self.last_full_text = ""
        
        # --- SISTEMA DE EQUIPO ---
        self.team = [None] * 6
        self.team_images = [None] * 6
        self._load_team()
        os.makedirs("sprites_cache", exist_ok=True) 
        # -------------------------
                    
        self._build_ui()
        self._load_zones() 
        self._load_mappings() 
        self._start_hardware_polling()
            
        threading.Thread(target=self._fetch_pokemon_list, daemon=True).start()
        threading.Thread(target=self._check_for_updates, daemon=True).start()
        
        self.root.after(500, self._check_tesseract_setup)
        self.root.after(200, self._render_team_ui)
        
        self.root.mainloop()

    # ---------------------------------------------------------
    # GESTIÓN DEL DIRECTORIO DE GUARDADO
    # ---------------------------------------------------------
    def _setup_save_directory(self):
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
        # Utilizamos la carpeta AppData del usuario para guardar la ruta elegida.
        # Esto soluciona problemas de permisos que hacen que se reinicie cada vez.
        appdata_dir = os.path.join(os.environ.get('LOCALAPPDATA', os.environ.get('APPDATA', os.path.expanduser('~'))), "PokeFinderSmartNLP")
        os.makedirs(appdata_dir, exist_ok=True)
        config_file = os.path.join(appdata_dir, "rutas_config.txt")
        
        save_dir = ""
        
        if os.path.exists(config_file):
            try:
                with open(config_file, "r") as f:
                    save_dir = f.read().strip()
            except Exception:
                pass
                
        # Si no hay directorio guardado o dejó de existir, preguntamos
        if not save_dir or not os.path.exists(save_dir):
            self.root.withdraw() 
            messagebox.showinfo("Configuración Inicial", "Por favor, selecciona en qué carpeta quieres que se guarden los datos, cachés y configuraciones del programa.", parent=self.root)
            
            chosen_dir = filedialog.askdirectory(title="Selecciona la carpeta para guardar los datos")
            
            if chosen_dir: 
                save_dir = os.path.join(chosen_dir, "PokeFinder_Data")
                os.makedirs(save_dir, exist_ok=True)
                
                try:
                    with open(config_file, "w") as f:
                        f.write(save_dir)
                except Exception:
                    pass
                
                # --- MIGRACIÓN DE ARCHIVOS DE VERSIONES ANTERIORES ---
                archivos_a_mover = ["team_config.json", "custom_fixes.json", "custom_mappings.json", "zones_config.json", "tesseract_path.txt"]
                
                for archivo in archivos_a_mover:
                    origen = os.path.join(base_dir, archivo)
                    destino = os.path.join(save_dir, archivo)
                    if os.path.exists(origen):
                        try:
                            shutil.move(origen, destino)
                        except Exception:
                            pass
                            
                sprites_origen = os.path.join(base_dir, "sprites_cache")
                sprites_destino = os.path.join(save_dir, "sprites_cache")
                if os.path.exists(sprites_origen) and not os.path.exists(sprites_destino):
                    try:
                        shutil.move(sprites_origen, sprites_destino)
                    except Exception:
                        pass
                # -------------------------------------------------------
            else:
                save_dir = base_dir
            
            self.root.deiconify() 

        os.chdir(save_dir)

    # ---------------------------------------------------------
    # SISTEMAS DE MEMORIA DE TEXTO Y EQUIPO
    # ---------------------------------------------------------
    def _load_team(self):
        if os.path.exists("team_config.json"):
            try:
                with open("team_config.json", "r") as f:
                    self.team = json.load(f)
                    while len(self.team) < 6: self.team.append(None)
                    self.team = self.team[:6]
            except:
                self.team = [None] * 6

    def _save_team(self):
        try:
            with open("team_config.json", "w") as f:
                json.dump(self.team, f)
        except Exception as e: print(e)

    def _load_custom_fixes(self):
        if os.path.exists("custom_fixes.json"):
            try:
                with open("custom_fixes.json", "r") as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_custom_fixes(self):
        try:
            with open("custom_fixes.json", "w") as f:
                json.dump(self.custom_fixes, f)
        except Exception as e:
            print(e)

    def _check_tesseract_setup(self):
        global TESSERACT_AVAILABLE
        if TESSERACT_AVAILABLE: return

        try: import pytesseract
        except ImportError:
            messagebox.showerror("Error crítico", "Falta el módulo de Python 'pytesseract'.", parent=self.root)
            return

        saved_path_file = "tesseract_path.txt"
        if os.path.exists(saved_path_file):
            try:
                with open(saved_path_file, "r") as f:
                    saved_path = f.read().strip()
                if os.path.exists(saved_path) and saved_path.lower().endswith("tesseract.exe"):
                    pytesseract.pytesseract.tesseract_cmd = saved_path
                    TESSERACT_AVAILABLE = True
                    return
            except: pass
                
        reg_path = self._find_tesseract_registry()
        if reg_path:
            pytesseract.pytesseract.tesseract_cmd = reg_path
            TESSERACT_AVAILABLE = True
            try:
                with open(saved_path_file, "w") as f:
                    f.write(reg_path)
            except: pass
            return

        has_tesseract = messagebox.askyesno(
            "Tesseract OCR no detectado", 
            "No se detectó Tesseract OCR, necesario para leer el texto en pantalla.\n\n¿Ya lo tenés instalado en tu computadora?",
            parent=self.root
        )

        if has_tesseract:
            path = simpledialog.askstring(
                "Ruta de Tesseract", 
                "Pegá la ruta completa hacia el archivo tesseract.exe\nEj: C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
                parent=self.root
            )
            if path:
                path = path.strip().strip('"').strip("'")
                if os.path.exists(path) and path.lower().endswith("tesseract.exe"):
                    pytesseract.pytesseract.tesseract_cmd = path
                    TESSERACT_AVAILABLE = True
                    try:
                        with open(saved_path_file, "w") as f:
                            f.write(path)
                    except: pass
                    messagebox.showinfo("Éxito", "Tesseract configurado correctamente.", parent=self.root)
                else:
                    messagebox.showerror("Error", "Ruta inválida. Asegurate de que termine en tesseract.exe. Reiniciá el programa para volver a intentar.", parent=self.root)
        else:
            do_install = messagebox.askyesno(
                "Instalar Tesseract",
                "Para que la aplicación funcione correctamente, se debe instalar Tesseract OCR.\n¿Querés que el programa lo descargue e instale por vos?",
                parent=self.root
            )
            if do_install:
                self._install_tesseract()
            else:
                messagebox.showwarning("Atención", "El programa no podrá leer la pantalla hasta que instales Tesseract OCR.", parent=self.root)

    def _install_tesseract(self):
        self.status_var.set("Descargando Tesseract OCR...")
        self.root.update()
        
        def download_and_install():
            import urllib.request
            import subprocess
            import tempfile
            import json
            
            try:
                req = urllib.request.Request("https://api.github.com/repos/UB-Mannheim/tesseract/releases/latest", headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode())
                    installer_url = next(a['browser_download_url'] for a in data.get('assets', []) if a['name'].endswith('.exe') and 'w64' in a['name'].lower())

                temp_dir = tempfile.gettempdir()
                installer_path = os.path.join(temp_dir, "tesseract_installer.exe")
                
                def tess_progress(block_num, block_size, total_size):
                    if total_size > 0:
                        percent = min(100, int(block_num * block_size * 100 / total_size))
                        self.root.after(0, lambda p=percent: self.status_var.set(f"Descargando Tesseract OCR... {p}%"))
                
                urllib.request.urlretrieve(installer_url, installer_path, tess_progress)
                
                self.root.after(0, lambda: self.status_var.set("Instalando Tesseract... Completá el instalador."))
                subprocess.run([installer_path], check=True)
                
                found_path = self._find_tesseract_registry()
                if not found_path:
                    common_paths = [
                        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                        r"D:\Program Files\Tesseract-OCR\tesseract.exe"
                    ]
                    for cp in common_paths:
                        if os.path.exists(cp):
                            found_path = cp
                            break
                            
                if found_path and os.path.exists(found_path):
                    import pytesseract
                    pytesseract.pytesseract.tesseract_cmd = found_path
                    global TESSERACT_AVAILABLE
                    TESSERACT_AVAILABLE = True
                    
                    try:
                        with open("tesseract_path.txt", "w") as f:
                            f.write(found_path)
                    except: pass
                    
                    self.root.after(0, lambda: self.status_var.set("Tesseract detectado correctamente."))
                    self.root.after(0, lambda: messagebox.showinfo("Éxito", f"Tesseract instalado y detectado en:\n{found_path}\n\n¡Listo para usar!", parent=self.root))
                else:
                    self.root.after(0, lambda: messagebox.showwarning("Aviso", "Tesseract se instaló pero no se pudo detectar automáticamente su ubicación.\nPor favor asigná la ruta manualmente la próxima vez.", parent=self.root))
            except Exception as e:
                self.root.after(0, lambda err=e: messagebox.showerror("Error", f"No se pudo instalar Tesseract:\n{err}", parent=self.root))
                self.root.after(0, lambda: self.status_var.set("Error al instalar Tesseract."))

        threading.Thread(target=download_and_install, daemon=True).start()

    def _find_tesseract_registry(self):
        import winreg
        paths_to_check = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall")
        ]
        
        for hkey, reg_path in paths_to_check:
            try:
                with winreg.OpenKey(hkey, reg_path) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                try:
                                    display_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                                    if "Tesseract-OCR" in str(display_name) or "Tesseract OCR" in str(display_name):
                                        install_location, _ = winreg.QueryValueEx(subkey, "InstallLocation")
                                        if install_location:
                                            exe_path = os.path.join(install_location, "tesseract.exe")
                                            if os.path.exists(exe_path):
                                                return exe_path
                                except OSError: pass
                        except OSError: pass
            except OSError: pass
        return None

    # ---------------------------------------------------------
    # SISTEMA DE AUTO-ACTUALIZACIÓN INTELIGENTE 
    # ---------------------------------------------------------
    def _check_for_updates(self):
        if not getattr(sys, 'frozen', False): return
        if REPO_OWNER == "TuUsuarioGitHub": return

        try:
            url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                latest_version = data.get('tag_name', 'Nueva Versión')
                
                for asset in data.get('assets', []):
                    if asset['name'].endswith('.exe'):
                        remote_size = asset['size']
                        local_size = os.path.getsize(sys.executable)
                        
                        if remote_size == local_size:
                            try:
                                with open("version_cache.txt", "w") as f: f.write(latest_version)
                            except: pass
                            self.root.after(0, lambda: self.root.title(f"🔴 Pokémon Finder (Smart NLP) - {latest_version}"))
                        else:
                            self.root.after(0, lambda: self.root.title(f"🔴 Pokémon Finder - (Actualización {latest_version} disponible)"))
                            download_url = asset['browser_download_url']
                            self.root.after(0, lambda: self._prompt_update(latest_version, download_url))
                        break
        except Exception as e:
            print(f"Error silencioso al buscar updates: {e}")

    def _prompt_update(self, version, download_url):
        if messagebox.askyesno("Actualización disponible", f"¡Hay una versión diferente publicada en GitHub ({version})!\n\n¿Querés descargarla y actualizar ahora?", parent=self.root):
            self.status_var.set("Descargando actualización...")
            self.root.update()
            threading.Thread(target=self._apply_update, args=(download_url,), daemon=True).start()

    def _apply_update(self, download_url):
        import subprocess
        exe_path = sys.executable
        new_exe_path = exe_path + ".new"
        old_exe_path = exe_path + ".old"
        
        def update_progress(block_num, block_size, total_size):
            if total_size > 0:
                percent = min(100, int(block_num * block_size * 100 / total_size))
                self.root.after(0, lambda p=percent: self.status_var.set(f"Descargando actualización... {p}%"))
        
        try:
            urllib.request.urlretrieve(download_url, new_exe_path, update_progress)
            if os.path.getsize(new_exe_path) < 1000000:
                raise Exception("El archivo descargado parece corrupto.")
            
            # Borrado preventivo
            if os.path.exists(old_exe_path):
                try: os.remove(old_exe_path)
                except Exception: pass 

            # Usar os.replace en vez de os.rename soluciona el problema de "archivo ya existe" en Windows
            try:
                os.replace(exe_path, old_exe_path)
            except Exception:
                # Fallback por si fallara la versión de Python o SO
                try: os.rename(exe_path, old_exe_path)
                except Exception: pass

            try:
                os.replace(new_exe_path, exe_path)
            except Exception:
                os.rename(new_exe_path, exe_path)

            clean_env = os.environ.copy()
            keys_to_remove = []
            for key in clean_env.keys():
                key_upper = key.upper()
                if 'MEI' in key_upper or 'TCL' in key_upper or 'TK' in key_upper or 'PYI' in key_upper:
                    keys_to_remove.append(key)
                    
            for key in keys_to_remove:
                clean_env.pop(key, None)
                
            if 'PATH' in clean_env:
                paths = clean_env['PATH'].split(os.pathsep)
                clean_env['PATH'] = os.pathsep.join([p for p in paths if '_MEI' not in p.upper()])

            DETACHED_PROCESS = 0x00000008
            subprocess.Popen([exe_path], env=clean_env, creationflags=DETACHED_PROCESS, close_fds=True)
            os._exit(0)
            
        except Exception as e:
            if os.path.exists(old_exe_path) and not os.path.exists(exe_path):
                try: os.replace(old_exe_path, exe_path)
                except: pass

            self.root.after(0, lambda err=e: messagebox.showerror("Error Update", f"Fallo al actualizar: {err}", parent=self.root))
            self.root.after(0, lambda: self.status_var.set("Listo."))

    # ---------------------------------------------------------
    # HARDWARE POLLING Y UI
    # ---------------------------------------------------------
    def _start_hardware_polling(self):
        if user32.GetAsyncKeyState(0x77) & 0x8000:
            if not self.f8_pressed:
                self.f8_pressed = True
                if not self.is_capturing and not self.overlay:
                    self.root.after(0, self._start_selection)
        else:
            self.f8_pressed = False

        for vk, data in list(self.zones.items()):
            if user32.GetAsyncKeyState(vk) & 0x8000:
                if not data["pressed"]:
                    data["pressed"] = True
                    if not self.is_capturing:
                        self.root.after(0, lambda c=data["coords"]: self._execute_physical_capture(c))
            else:
                data["pressed"] = False

        self.root.after(40, self._start_hardware_polling)

    def _build_ui(self):
        header = tk.Frame(self.root, bg="#16213e", pady=8)
        header.pack(fill="x")
        try:
            ruta_logo = resource_path("icono.ico") 
            imagen_original = Image.open(ruta_logo)
            
            if hasattr(Image, "Resampling"): imagen_redimensionada = imagen_original.resize((24, 24), Image.Resampling.LANCZOS)
            else: imagen_redimensionada = imagen_original.resize((24, 24), Image.LANCZOS)
                
            self.logo_img = ImageTk.PhotoImage(imagen_redimensionada)
            tk.Label(header, text=" Pokémon Finder Smart NLP", image=self.logo_img, compound="left", font=("Arial", 16, "bold"), fg="#e94560", bg="#16213e").pack()
        except Exception:
            tk.Label(header, text="🜔 Pokémon Finder Smart NLP", font=("Arial", 16, "bold"), fg="#e94560", bg="#16213e").pack()
        tk.Label(header, text="Multizona + Autocorrector Persistente", font=("Arial", 9), fg="#a0a0c0", bg="#16213e").pack()

        frame_cap = tk.LabelFrame(self.root, text=" 📐 1. Mapear Cajas de Texto ", fg="#e94560", bg="#1a1a2e", font=("Arial", 10, "bold"), pady=4, padx=10)
        frame_cap.pack(fill="x", padx=15, pady=(10, 2))

        tk.Label(frame_cap, text="Trazá cajas de diálogo. Se guardarán automáticamente.", fg="#a0a0c0", bg="#1a1a2e", font=("Arial", 8), wraplength=380, justify="left").pack(anchor="w", pady=(0, 4))
        tk.Button(frame_cap, text="+ Nueva caja de diálogo (F8)", command=self._start_selection, bg="#e94560", fg="white", font=("Arial", 11, "bold"), relief="flat", cursor="hand2", pady=4).pack(fill="x")
        
        tk.Button(frame_cap, text="⚙️ Gestionar / Borrar Zonas", command=self._manage_zones, bg="#252538", fg="#ffdd88", font=("Arial", 9, "bold"), relief="flat", cursor="hand2", pady=2).pack(fill="x", pady=(4, 0))
        
        self.preview_label = tk.Label(frame_cap, bg="#0f3460", text="Vista previa de captura\n(Esperando...)", fg="#606080", font=("Arial", 9), pady=5)
        self.preview_label.pack(pady=4, fill="x")

        frame_info = tk.Frame(self.root, bg="#1a1a2e")
        frame_info.pack(fill="x", padx=15, pady=2)
        
        self.zones_var = tk.StringVar(value="🎯 Zonas activas: Ninguna")
        tk.Label(frame_info, textvariable=self.zones_var, fg="#4ade80", bg="#1a1a2e", font=("Arial", 9, "bold")).pack()

        frame_debug = tk.LabelFrame(self.root, text=" 🔬 Motor NLP (Extracción) ", fg="#e94560", bg="#1a1a2e", font=("Arial", 10, "bold"), pady=4, padx=10)
        frame_debug.pack(fill="x", padx=15, pady=2)

        self.raw_text_var = tk.StringVar(value="(Texto crudo...)")
        tk.Label(frame_debug, textvariable=self.raw_text_var, fg="#a0a0c0", bg="#1a1a2e", font=("Arial", 8), wraplength=370, justify="left").pack(anchor="w")
        
        self.debug_var = tk.StringVar(value="(Resultado...)")
        tk.Label(frame_debug, textvariable=self.debug_var, fg="#ffdd88", bg="#1a1a2e", font=("Courier", 10, "bold"), wraplength=370, justify="left").pack(anchor="w", pady=(2,0))

        tk.Button(frame_debug, text="✏️ Corregir Última Captura", command=self._correct_last_capture, bg="#252538", fg="#ffaa00", font=("Arial", 8, "bold"), relief="flat", cursor="hand2", pady=2).pack(fill="x", pady=(4,0))
        tk.Button(frame_debug, text="🧠 Gestionar Decisiones Aprendidas", command=self._manage_mappings, bg="#252538", fg="#4ade80", font=("Arial", 8, "bold"), relief="flat", cursor="hand2", pady=2).pack(fill="x", pady=(4,0))

        # --- SECCIÓN DEL EQUIPO POKÉMON ---
        frame_team = tk.LabelFrame(self.root, text=" 🛡️ Mi Equipo (Acceso Rápido) ", fg="#e94560", bg="#1a1a2e", font=("Arial", 10, "bold"), pady=4, padx=10)
        frame_team.pack(fill="x", padx=15, pady=2)
        
        self.team_buttons = []
        team_grid = tk.Frame(frame_team, bg="#1a1a2e")
        team_grid.pack(pady=2)
        
        for i in range(6):
            slot_frame = tk.Frame(team_grid, width=54, height=54, bg="#252538")
            slot_frame.pack_propagate(False)
            slot_frame.grid(row=0, column=i, padx=4)
            
            btn = tk.Button(slot_frame, text="+", bg="#252538", fg="#a0a0c0", font=("Arial", 14, "bold"),
                            relief="flat", cursor="hand2", activebackground="#e94560",
                            command=lambda idx=i: self._on_team_slot_click(idx))
            btn.bind("<Button-3>", lambda e, idx=i: self._on_team_slot_right_click(idx))
            btn.pack(fill="both", expand=True)
            self.team_buttons.append(btn)
            
        tk.Label(frame_team, text="Click izq: Abrir / Añadir | Click derecho: Quitar del equipo", fg="#606080", bg="#1a1a2e", font=("Arial", 8)).pack(pady=(4,0))
        # ----------------------------------

        bottom_frame = tk.Frame(self.root, bg="#1a1a2e")
        bottom_frame.pack(side="bottom", fill="x", padx=15, pady=5)

        self.status_var = tk.StringVar(value="Iniciando sistema...")
        tk.Label(bottom_frame, textvariable=self.status_var, fg="#808098", bg="#1a1a2e", font=("Arial", 8)).pack(side="left", anchor="sw")

        credits_text = "Created by: Juan Esteban Kromberger\n                Gino Laprovida"
        tk.Label(bottom_frame, text=credits_text, fg="#606080", bg="#1a1a2e", font=("Arial", 7, "bold"), justify="right").pack(side="right", anchor="se")

    # ---------------------------------------------------------
    # FUNCIONES DEL EQUIPO (ACCESOS RÁPIDOS)
    # ---------------------------------------------------------
    def _on_team_slot_click(self, index):
        poke = self.team[index]
        if poke:
            self._search_pokemon(poke)
        else:
            self._prompt_add_team(index)
            
    def _on_team_slot_right_click(self, index):
        if self.team[index]:
            name = self.team[index]
            if messagebox.askyesno("Quitar del equipo", f"¿Querés quitar a {name.capitalize()} de este espacio?", parent=self.root):
                self.team[index] = None
                self._save_team()
                self._render_team_ui()

    def _prompt_add_team(self, index):
        self.root.deiconify()
        name = simpledialog.askstring("Añadir al Equipo", "Ingresá el nombre exacto del Pokémon:", parent=self.root)
        if name:
            name = name.lower().strip()
            if name in self.known_pokemon or not self.pokemon_ids:
                self.team[index] = name
                self._save_team()
                self._render_team_ui()
                self.status_var.set(f"✅ {name.capitalize()} añadido al equipo.")
            else:
                messagebox.showwarning("No encontrado", f"No reconozco a '{name}'. Asegurate de escribirlo bien.", parent=self.root)

    def _render_team_ui(self):
        for i, poke in enumerate(self.team):
            btn = self.team_buttons[i]
            if poke:
                self._load_and_set_sprite(poke, i, btn)
            else:
                btn.config(image="", text="+", bg="#252538")
                self.team_images[i] = None

    def _load_and_set_sprite(self, name, index, btn):
        cache_path = os.path.join("sprites_cache", f"{name}.png")
        
        def load_local():
            try:
                img = Image.open(cache_path).convert("RGBA")
                if hasattr(Image, "Resampling"):
                    img = img.resize((50, 50), Image.Resampling.LANCZOS)
                else:
                    img = img.resize((50, 50), Image.LANCZOS)
                    
                tk_img = ImageTk.PhotoImage(img)
                self.team_images[index] = tk_img 
                self.root.after(0, lambda: btn.config(image=tk_img, text="", bg="#1a1a2e"))
            except Exception:
                self.root.after(0, lambda: btn.config(image="", text=name[:3].capitalize(), bg="#4ade80", fg="#1a1a2e"))

        def download_and_load():
            poke_id = self.pokemon_ids.get(name)
            if poke_id:
                url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{poke_id}.png"
            else:
                url = f"https://play.pokemonshowdown.com/sprites/gen5/{name}.png"
            
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as response:
                    img_data = response.read()
                    with open(cache_path, "wb") as f:
                        f.write(img_data)
                self.root.after(0, load_local)
            except Exception:
                self.root.after(0, load_local) 
                
        if os.path.exists(cache_path):
            load_local()
        else:
            threading.Thread(target=download_and_load, daemon=True).start()

    # ---------------------------------------------------------
    # SELECCIÓN Y GESTIÓN DE ZONAS
    # ---------------------------------------------------------
    def _start_selection(self):
        if not MSS_AVAILABLE or self.is_capturing: return
        self.root.withdraw()
        self.root.update()

        self.overlay = tk.Toplevel()
        self.overlay.attributes("-fullscreen", True)
        self.overlay.attributes("-alpha", 0.3)
        self.overlay.configure(bg="black")
        self.overlay.attributes("-topmost", True)

        self.canvas = tk.Canvas(self.overlay, bg="black", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.overlay.bind("<Escape>", lambda e: self._close_overlay())

    def _on_press(self, event):
        self.start_x, self.start_y = event.x_root, event.y_root
        self.rect_id = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, outline="#e94560", width=2)

    def _on_drag(self, event):
        ox, oy = self.overlay.winfo_rootx(), self.overlay.winfo_rooty()
        self.canvas.coords(self.rect_id, self.start_x - ox, self.start_y - oy, event.x, event.y)

    def _on_release(self, event):
        end_x, end_y = event.x_root, event.y_root
        self._close_overlay()
        
        x1, y1 = min(self.start_x, end_x), min(self.start_y, end_y)
        x2, y2 = max(self.start_x, end_x), max(self.start_y, end_y)
        
        if x2 - x1 < 8 or y2 - y1 < 8: return
        
        coords = (x1, y1, x2, y2)
        self.root.after(100, lambda: self._ask_key(coords))

    def _ask_key(self, coords):
        self.root.deiconify()
        self.key_win = tk.Toplevel(self.root)
        self.key_win.title("⌨️ Asignar Tecla")
        self.key_win.geometry("300x120")
        self.key_win.configure(bg="#16213e")
        self.key_win.attributes("-topmost", True)
        
        self.key_win.transient(self.root)
        self.key_win.grab_set()
        self.key_win.focus_force()
        
        tk.Label(self.key_win, text="Presioná la tecla para buscar en esta zona\n(Ej: F4, Q, 1, etc.)", fg="#4ade80", bg="#16213e", font=("Arial", 10, "bold")).pack(pady=30)
        
        self.key_win.bind("<Key>", lambda e: self._save_key(e, coords))

    def _save_key(self, event, coords):
        vk = event.keycode
        name = event.keysym.upper()
        
        self.zones[vk] = {"name": name, "coords": coords, "pressed": False}
        self.key_win.destroy()
        
        self._save_zones_to_disk()
        self._update_zones_ui()
        self.status_var.set(f"✅ Zona guardada en la tecla {name}.")

    def _save_zones_to_disk(self):
        try:
            with open("zones_config.json", "w") as f:
                json.dump(self.zones, f)
        except Exception as e:
            print(f"Error al guardar zonas: {e}")

    def _load_zones(self):
        if os.path.exists("zones_config.json"):
            try:
                with open("zones_config.json", "r") as f:
                    data = json.load(f)
                    self.zones = {int(k): v for k, v in data.items()}
                self._update_zones_ui()
                self.status_var.set("✅ Configuración de zonas cargada.")
            except Exception as e:
                print(f"Error al cargar zonas: {e}")

    def _manage_zones(self):
        if not self.zones:
            messagebox.showinfo("Zonas", "No hay zonas activas para borrar.", parent=self.root)
            return

        self.manage_win = tk.Toplevel(self.root)
        self.manage_win.title("⚙️ Gestionar Zonas")
        self.manage_win.geometry("280x350")
        self.manage_win.configure(bg="#16213e")
        self.manage_win.attributes("-topmost", True)
        
        self.manage_win.transient(self.root)
        self.manage_win.grab_set()
        self.manage_win.focus_force()

        tk.Label(self.manage_win, text="Tus Zonas Activas:", fg="#e94560", bg="#16213e", font=("Arial", 11, "bold")).pack(pady=12)

        self.list_frame = tk.Frame(self.manage_win, bg="#16213e")
        self.list_frame.pack(fill="both", expand=True, padx=15, pady=5)

        self._refresh_manage_window()

    def _refresh_manage_window(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        if not self.zones:
            self.manage_win.destroy()
            return

        for vk, data in list(self.zones.items()):
            row = tk.Frame(self.list_frame, bg="#1a1a2e", pady=8, padx=10)
            row.pack(fill="x", pady=4)
            
            tk.Label(row, text=f"Tecla: {data['name']}", fg="#4ade80", bg="#1a1a2e", font=("Arial", 10, "bold")).pack(side="left")
            tk.Button(row, text="❌ Borrar", bg="#e94560", fg="white", font=("Arial", 8, "bold"), relief="flat", cursor="hand2",
                      command=lambda k=vk: self._delete_single_zone(k)).pack(side="right")

    def _delete_single_zone(self, vk):
        if vk in self.zones:
            key_name = self.zones[vk]['name']
            del self.zones[vk]
            self._save_zones_to_disk()
            self._update_zones_ui()
            
            if not self.zones:
                self.preview_label.config(image="", text="Vista previa de captura\n(Esperando...)")
                
            self.status_var.set(f"✅ Zona '{key_name}' eliminada.")
            self._refresh_manage_window()

    def _update_zones_ui(self):
        if self.zones:
            nombres = [d["name"] for d in self.zones.values()]
            self.zones_var.set(f"🎯 Zonas en teclas: {', '.join(nombres)}")
        else:
            self.zones_var.set("🎯 Zonas activas: Ninguna")

    def _close_overlay(self):
        if self.overlay:
            self.overlay.destroy()
            self.overlay = None

    # ---------------------------------------------------------
    # CAPTURA Y MOTOR NLP
    # ---------------------------------------------------------
    def _execute_physical_capture(self, coords):
        if not MSS_AVAILABLE:
            messagebox.showerror("Librería faltante", "La librería de captura 'mss' no está disponible o falló al cargarse. No se puede realizar la captura.", parent=self.root)
            return

        self.is_capturing = True
        self.status_var.set("Limpiando caché de imagen y texto...")
        
        self.tk_preview = None 
        self.preview_label.config(image="", text="📷 Tomando foto...\n ")
        self.raw_text_var.set("(Limpiando...)")
        self.debug_var.set("(Procesando...)")
        
        self.root.update_idletasks() 
        self.root.withdraw()
        self.root.update()
        
        threading.Thread(target=self._async_grab, args=(coords,), daemon=True).start()

    def _async_grab(self, coords):
        try:
            time.sleep(0.2) 
            x1, y1, x2, y2 = coords
            monitor = {"top": y1, "left": x1, "width": x2 - x1, "height": y2 - y1}

            with mss.MSS() as sct:
                sct_img = sct.grab(monitor)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

            self._run_nlp_engine(img)

        except Exception as e:
            self.root.after(0, lambda err=e: self.debug_var.set(f"Error: {str(err)}"))
            self.root.after(0, self._restore_ui)

    def _run_nlp_engine(self, img):
        if not TESSERACT_AVAILABLE: 
            self.root.after(0, lambda: self.debug_var.set("❌ Tesseract no encontrado."))
            self.root.after(0, self._restore_ui)
            return

        best_match = None
        full_text_detected = ""
        found_pokemon_list = []

        ignore_words = {"nv", "lv", "lvl", "ps", "hp", "cp", "exp"}

        for variant_img in self._get_image_variants(img):
            for psm in (7, 8, 6, 3): 
                try:
                    cfg = f"--oem 3 --psm {psm} -l eng"
                    text = pytesseract.image_to_string(variant_img, config=cfg).strip()
                    
                    clean_display = re.sub(r'[^a-zA-Z0-9\s]', '', text)
                    if len(clean_display) > len(full_text_detected):
                        full_text_detected = clean_display 
                        
                    merged_word = re.sub(r'[^a-zA-Z]', '', text.lower())
                    
                    if merged_word in self.custom_fixes: 
                        if self.custom_fixes[merged_word] not in found_pokemon_list:
                            found_pokemon_list.append(self.custom_fixes[merged_word])
                    else:
                        for poke in self.known_pokemon:
                            if len(poke) >= 3 and poke in merged_word and poke not in found_pokemon_list:
                                found_pokemon_list.append(poke)
                    
                    clean_text = re.sub(r'[^a-zA-Z\s]', '', text.lower())
                    for w in clean_text.split():
                        if w in ignore_words or len(w) < 4: 
                            continue
                        
                        if w in self.known_pokemon and w not in found_pokemon_list:
                            found_pokemon_list.append(w)
                        else:
                            matches = difflib.get_close_matches(w, self.known_pokemon, n=1, cutoff=0.75)
                            if matches and matches[0] not in found_pokemon_list:
                                found_pokemon_list.append(matches[0])
                            
                except Exception: pass
            
            if found_pokemon_list: break

        self.last_full_text = full_text_detected
        self.last_raw_clean = re.sub(r'[^a-zA-Z]', '', full_text_detected.lower())

        self.root.after(0, lambda: self.raw_text_var.set(f"Texto detectado: {full_text_detected[:100]}..."))

        if not found_pokemon_list:
            self.root.after(0, lambda: self._ask_manual_pokemon(full_text_detected, img))
            return

        found_pokemon_list = list(dict.fromkeys(found_pokemon_list))

        if len(found_pokemon_list) == 1:
            best_match = found_pokemon_list[0].capitalize()
            self._finish_success(best_match, found_pokemon_list, img)
            
        else:
            mapping_key = ",".join(sorted(found_pokemon_list))
            
            if mapping_key in self.custom_mappings:
                best_match = self.custom_mappings[mapping_key].capitalize()
                self._finish_success(best_match, found_pokemon_list, img)
            else:
                self.root.after(0, lambda: self._ask_user_for_pokemon(found_pokemon_list, mapping_key, img))

    def _correct_last_capture(self):
        if not hasattr(self, 'last_raw_clean') or not self.last_raw_clean:
            messagebox.showwarning("Aviso", "Primero tenés que hacer una captura para poder corregirla.", parent=self.root)
            return

        self.root.deiconify()
        manual_poke = simpledialog.askstring(
            "✏️ Corregir Detección",
            f"Último texto leído por la cámara:\n'{self.last_full_text}'\n\nSi detectó un Pokémon incorrecto, ingresá el nombre real para enseñárselo y buscarlo:",
            parent=self.root
        )

        if manual_poke:
            manual_poke = manual_poke.lower().strip()
            self.custom_fixes[self.last_raw_clean] = manual_poke
            self._save_custom_fixes()
            
            self.known_pokemon.add(manual_poke)
            
            self.debug_var.set(f"✔️ Aprendido: Ese texto es {manual_poke.capitalize()}")
            self.status_var.set("✅ Corrección guardada exitosamente.")
            
            self._search_pokemon(manual_poke.capitalize())

    def _ask_manual_pokemon(self, full_text, img):
        self.root.deiconify() 
        manual_poke = simpledialog.askstring("Pokémon no detectado", f"Texto leído: '{full_text}'\n\nNo se reconoció. Ingresá el nombre correcto para buscarlo y recordarlo:", parent=self.root)
        
        if manual_poke:
            manual_poke = manual_poke.lower().strip()
            raw_clean = re.sub(r'[^a-zA-Z]', '', full_text.lower())
            
            if raw_clean: 
                self.custom_fixes[raw_clean] = manual_poke
                self._save_custom_fixes()
                
            self.known_pokemon.add(manual_poke)
                
            self._finish_success(manual_poke.capitalize(), [manual_poke], img)
        else:
            self.debug_var.set("❌ Búsqueda cancelada.")
            self._update_preview(img)
            self._restore_ui()
        
    def _save_mappings_to_disk(self):
        try:
            with open("custom_mappings.json", "w") as f:
                json.dump(self.custom_mappings, f)
        except Exception as e: print(e)

    def _load_mappings(self):
        if os.path.exists("custom_mappings.json"):
            try:
                with open("custom_mappings.json", "r") as f:
                    self.custom_mappings = json.load(f)
            except Exception as e: print(e)

    def _ask_user_for_pokemon(self, options, mapping_key, img):
        self.root.deiconify() 
        
        self.ask_win = tk.Toplevel(self.root)
        self.ask_win.title("🤔 Múltiples coincidencias")
        self.ask_win.geometry("300x350")
        self.ask_win.configure(bg="#16213e")
        self.ask_win.attributes("-topmost", True)
        
        self.ask_win.transient(self.root)
        self.ask_win.grab_set()
        self.ask_win.focus_force()
        
        tk.Label(self.ask_win, text="¡El detector está en duda!\n¿Cuál es el Pokémon correcto?", fg="#ffdd88", bg="#16213e", font=("Arial", 10, "bold")).pack(pady=15)
        
        frame_btns = tk.Frame(self.ask_win, bg="#16213e")
        frame_btns.pack(fill="both", expand=True, padx=20)
        
        for poke in options:
            btn = tk.Button(frame_btns, text=poke.capitalize(), bg="#e94560", fg="white", font=("Arial", 10, "bold"), relief="flat", cursor="hand2", 
                            command=lambda p=poke: self._save_user_choice(p, options, mapping_key, img))
            btn.pack(fill="x", pady=6)
            
        tk.Button(frame_btns, text="❌ Cancelar Búsqueda", bg="#252538", fg="white", font=("Arial", 9), relief="flat", cursor="hand2", 
                  command=lambda: self._cancel_ask(img)).pack(fill="x", pady=20)

    def _save_user_choice(self, chosen_poke, all_options, mapping_key, img):
        self.custom_mappings[mapping_key] = chosen_poke
        self._save_mappings_to_disk()
        
        self.known_pokemon.add(chosen_poke.lower())
        
        self.ask_win.destroy()
        self.status_var.set(f"✅ Aprendido: {chosen_poke.capitalize()}")
        self._finish_success(chosen_poke.capitalize(), all_options, img)
        
    def _cancel_ask(self, img):
        self.ask_win.destroy()
        self.debug_var.set("❌ Captura cancelada (Duda no resuelta).")
        self._update_preview(img)
        self._restore_ui()

    def _manage_mappings(self):
        if not self.custom_mappings and not self.custom_fixes:
            messagebox.showinfo("Decisiones", "Todavía no le enseñaste ninguna decisión al programa.", parent=self.root)
            return

        self.map_win = tk.Toplevel(self.root)
        self.map_win.title("🧠 Decisiones Aprendidas")
        self.map_win.geometry("340x400")
        self.map_win.configure(bg="#16213e")
        self.map_win.attributes("-topmost", True)
        
        self.map_win.transient(self.root)
        self.map_win.grab_set()
        self.map_win.focus_force()

        tk.Label(self.map_win, text="Tu historial de correcciones:", fg="#4ade80", bg="#16213e", font=("Arial", 11, "bold")).pack(pady=12)

        canvas = tk.Canvas(self.map_win, bg="#16213e", highlightthickness=0)
        scrollbar = tk.Scrollbar(self.map_win, orient="vertical", command=canvas.yview)
        self.map_frame = tk.Frame(canvas, bg="#16213e")

        self.map_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.map_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=10)
        scrollbar.pack(side="right", fill="y")

        self._refresh_map_window()

    def _refresh_map_window(self):
        for widget in self.map_frame.winfo_children():
            widget.destroy()

        if not self.custom_mappings and not self.custom_fixes:
            self.map_win.destroy()
            return

        if self.custom_mappings:
            tk.Label(self.map_frame, text="--- Conflictos Resueltos ---", fg="#ffdd88", bg="#16213e", font=("Arial", 9)).pack(pady=5)
            for key, chosen in list(self.custom_mappings.items()):
                row = tk.Frame(self.map_frame, bg="#1a1a2e", pady=8, padx=10)
                row.pack(fill="x", pady=4)
                
                conflict_text = " vs ".join([p.capitalize() for p in key.split(",")])
                lbl_text = f"Dudó en:\n{conflict_text}\n✔️ Elegiste: {chosen.capitalize()}"
                
                tk.Label(row, text=lbl_text, fg="#a0a0c0", bg="#1a1a2e", font=("Arial", 8, "bold"), justify="left").pack(side="left")
                tk.Button(row, text="❌ Borrar", bg="#e94560", fg="white", font=("Arial", 8, "bold"), relief="flat", cursor="hand2",
                          command=lambda k=key: self._delete_single_mapping(k, is_fix=False)).pack(side="right")

        if self.custom_fixes:
            tk.Label(self.map_frame, text="--- Textos Raros Aprendidos ---", fg="#ffdd88", bg="#16213e", font=("Arial", 9)).pack(pady=5)
            for raw_text, chosen in list(self.custom_fixes.items()):
                row = tk.Frame(self.map_frame, bg="#1a1a2e", pady=8, padx=10)
                row.pack(fill="x", pady=4)
                
                lbl_text = f"Leía basura:\n'{raw_text}'\n✔️ Le enseñaste: {chosen.capitalize()}"
                
                tk.Label(row, text=lbl_text, fg="#a0a0c0", bg="#1a1a2e", font=("Arial", 8, "bold"), justify="left").pack(side="left")
                tk.Button(row, text="❌ Borrar", bg="#e94560", fg="white", font=("Arial", 8, "bold"), relief="flat", cursor="hand2",
                          command=lambda k=raw_text: self._delete_single_mapping(k, is_fix=True)).pack(side="right")

    def _delete_single_mapping(self, key, is_fix=False):
        if is_fix and key in self.custom_fixes:
            del self.custom_fixes[key]
            self._save_custom_fixes()
        elif not is_fix and key in self.custom_mappings:
            del self.custom_mappings[key]
            self._save_mappings_to_disk()
            
        self._refresh_map_window()
        self.status_var.set("🗑️ Decisión borrada.")

    def _finish_success(self, best_match, all_found, img):
        debug_txt = f"🔍 Entidades: {', '.join([p.capitalize() for p in all_found])}\n"
        debug_txt += f"🎯 SELECCIONADO: {best_match}"
        
        self.root.after(0, lambda: self.debug_var.set(debug_txt))
        self.root.after(0, lambda: self._update_preview(img))
        self.root.after(0, lambda m=best_match: self._search_pokemon(m))
        self.root.after(0, self._restore_ui)

    def _restore_ui(self):
        self.root.iconify() 
        self.status_var.set("Listo.")
        self.is_capturing = False

    def _update_preview(self, img):
        preview = img.copy()
        
        if hasattr(Image, "Resampling"): preview.thumbnail((380, 150), Image.Resampling.LANCZOS)
        else: preview.thumbnail((380, 150), Image.LANCZOS)
            
        self.tk_preview = ImageTk.PhotoImage(preview)
        self.preview_label.config(image=self.tk_preview, text="")

    def _get_image_variants(self, img):
        w, h = img.size
        if hasattr(Image, "Resampling"): big = img.resize((w * 4, h * 4), Image.Resampling.LANCZOS)
        else: big = img.resize((w * 4, h * 4), Image.LANCZOS)
            
        gray = ImageOps.autocontrast(big.convert("L"))
        
        yield gray.point(lambda p: 0 if p > 210 else 255)
        yield gray.point(lambda p: 0 if p > 160 else 255)
        yield ImageOps.invert(gray)
        yield gray.point(lambda p: 255 if p > 130 else 0)

    
    def _clean_api_name(self, api_name):
        """
        Limpia los sufijos de la API (-altered, -mega) conservando las excepciones
        que legítimamente llevan guion en su nombre base para PokémonDB.
        """
        exceptions = {
            "ho-oh", "porygon-z", "jangmo-o", "hakamo-o", "kommo-o",
            "tapu-koko", "tapu-lele", "tapu-bulu", "tapu-fini",
            "chi-yu", "chien-pao", "ting-lu", "wo-chien",
            "mr-mime", "mr-rime", "mime-jr", "type-null",
            "nidoran-f", "nidoran-m"
        }
        
        if api_name in exceptions:
            return api_name
        
        # Eliminar cualquier sufijo a partir del primer guion (ej: giratina-altered -> giratina)
        if "-" in api_name:
            return api_name.split("-")[0]
        
        return api_name
    
    def _fetch_pokemon_list(self):
        try:
            req = urllib.request.Request("https://pokeapi.co/api/v2/pokemon?limit=2000", headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                
                for p in data['results']:
                    original_name = p['name'].lower()
                    # Pasamos el nombre por nuestro filtro
                    clean_name = self._clean_api_name(original_name)
                    
                    self.known_pokemon.add(clean_name)
                    
                    poke_id = p['url'].strip('/').split('/')[-1]
                    # Solo guardamos el ID si no existe todavía (prioriza las formas base sobre las megas)
                    if clean_name not in self.pokemon_ids:
                        self.pokemon_ids[clean_name] = poke_id
                
            for poke in self.custom_fixes.values():
                self.known_pokemon.add(poke.lower())
            for poke in self.custom_mappings.values():
                self.known_pokemon.add(poke.lower())

            self.root.after(0, lambda: self.status_var.set(f"✅ Base de datos cargada ({len(self.known_pokemon)})."))
        except:
            self.root.after(0, lambda: self.status_var.set("⚠️ Error de red. Modo Offline."))

    def _search_pokemon(self, name):
        if not name: return
        
        # Formateo estricto para PokemonDB (ej: "Mr. Mime" -> "mr-mime", "Farfetch'd" -> "farfetchd")
        url_name = name.lower().strip()
        url_name = re.sub(r'[^a-z0-9\-\s]', '', url_name) # Quita puntos, apóstrofes y símbolos raros
        url_name = url_name.replace(" ", "-") # Reemplaza los espacios por guiones
        
        url = f"https://pokemondb.net/pokedex/{urllib.parse.quote(url_name)}"
        try: 
            webbrowser.open_new_tab(url)
        except Exception as e: 
            print(e)

if __name__ == "__main__":
    import ctypes
    import sys
    
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except:
        is_admin = False
        
    if not is_admin:
        try:
            if getattr(sys, 'frozen', False):
                argumentos = " ".join(sys.argv[1:])
            else:
                argumentos = " ".join([f'"{arg}"' for arg in sys.argv])
                
            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, argumentos, None, 1)
            if ret <= 32:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror("Permisos denegados", "El programa necesita permisos de Administrador para instalar Tesseract y funcionar correctamente.\n\nPor favor, hacé clic derecho en el ejecutable y seleccioná 'Ejecutar como administrador', o aceptá la solicitud de permisos.")
                root.destroy()
        except Exception:
            pass
        sys.exit(0)
        
    PokemonFinderNLP()