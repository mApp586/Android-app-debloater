import customtkinter
import subprocess
import os
import sys
import threading
import queue
import inspect  # Import inspect to check method signatures

# --- Global Queue for UI Updates from Background Threads ---
ui_update_queue = queue.Queue()


# --- resource_path function ---
def resource_path(relative_path):
    """
    Get the absolute path to a resource, useful for PyInstaller.
    This function expects relative_path to be a valid string, not None.
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    # No longer checks for None here; the caller ensures it's not None.
    return os.path.join(base_path, relative_path)


# --- CTkMessageBox Class ---
class CTkMessageBox(customtkinter.CTkToplevel):
    """
    A customizable message box for CustomTkinter applications.
    Can be used for info, warning, or error messages.
    """

    def __init__(self, parent_window, title="Message", message="Default message.",
                 icon_type="info", button_text="OK", width=300, height=150):
        # Debug print to confirm this __init__ is being called
        print(f"[DEBUG_MSG_BOX] CTkMessageBox __init__ called with signature: {inspect.signature(self.__init__)}")

        super().__init__(parent_window)

        self.title(title)
        self.geometry(f"{width}x{height}")
        self.transient(parent_window)  # Make dialog close with parent
        self.grab_set()  # Make dialog modal (blocks parent interaction)

        # Center the dialog on the parent window
        parent_window.update_idletasks()
        x = parent_window.winfo_x() + (parent_window.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent_window.winfo_y() + (parent_window.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

        self.resizable(True, True)

        # Configure grid layout for content
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Message Label
        self.message_label = customtkinter.CTkLabel(
            self,
            text=message,
            wraplength=width - 40,
            justify="center",
            font=customtkinter.CTkFont(size=14)
        )
        self.message_label.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        # OK Button
        self.ok_button = customtkinter.CTkButton(
            self,
            text=button_text,
            command=self.destroy
        )
        self.ok_button.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="s")

        # Set appearance based on icon_type
        if icon_type == "error":
            self.message_label.configure(text_color="red")
            self.ok_button.configure(fg_color="red", hover_color="darkred")
        elif icon_type == "warning":
            self.message_label.configure(text_color="orange")
            self.ok_button.configure(fg_color="orange", hover_color="darkorange")

        self.protocol("WM_DELETE_WINDOW", self.destroy)


class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        # --- Window Configuration ---
        self.title("USB Android App Debloater")
        self.geometry("850x650")
        self.resizable(False, False)

        # Configure grid layout for the main window (1 row, 2 columns)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.app_list_wraplength = 390

        # --- Control Panel Frame (Left Side) ---
        self.control_frame = customtkinter.CTkFrame(self, width=200, corner_radius=10)
        self.control_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.control_frame.grid_rowconfigure(7, weight=1)  # Adjusted for new About button

        # Device selection label
        self.device_label = customtkinter.CTkLabel(self.control_frame, text="Select Device:")
        self.device_label.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w")

        # Device selection ComboBox
        self.device_combobox = customtkinter.CTkComboBox(self.control_frame,
                                                         values=[],
                                                         command=self.on_device_selected)
        self.device_combobox.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")

        # Refresh devices button
        self.refresh_button = customtkinter.CTkButton(self.control_frame,
                                                      text="Refresh Devices",
                                                      command=self.populate_device_combobox)
        self.refresh_button.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        # Search label
        self.search_label = customtkinter.CTkLabel(self.control_frame, text="Search Package:")
        self.search_label.grid(row=3, column=0, padx=10, pady=(10, 0), sticky="w")

        # Search Entry Box
        self.search_entry = customtkinter.CTkEntry(self.control_frame,
                                                   placeholder_text="Enter package name or part...")
        self.search_entry.grid(row=4, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.search_entry.bind("<KeyRelease>", self.on_search_change)

        # Status label for operations like deletion
        self.status_label = customtkinter.CTkLabel(self.control_frame, text="", text_color="green", wraplength=180)
        self.status_label.grid(row=5, column=0, padx=10, pady=(0, 10), sticky="ew")

        # --- About Me Button ---
        self.about_button = customtkinter.CTkButton(
            self.control_frame,
            text="About This App",
            command=self.about_me
        )
        self.about_button.grid(row=6, column=0, padx=10, pady=10, sticky="ew")

        # --- App Display Container (Right Side) ---
        self.app_display_container = customtkinter.CTkFrame(self, corner_radius=10)
        self.app_display_container.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.app_display_container.grid_rowconfigure(0, weight=1)
        self.app_display_container.grid_rowconfigure(1, weight=1)
        self.app_display_container.grid_columnconfigure(0, weight=1)

        # --- External Apps Scrollable Frame ---
        self.external_apps_scroll_frame = customtkinter.CTkScrollableFrame(
            self.app_display_container,
            label_text="External Apps:",
            height=250,
            corner_radius=10
        )
        self.external_apps_scroll_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew")
        self.external_apps_scroll_frame.grid_columnconfigure(0, weight=1)
        self.external_apps_scroll_frame.grid_columnconfigure(1, weight=0)

        # --- System Apps Scrollable Frame ---
        self.system_apps_scroll_frame = customtkinter.CTkScrollableFrame(
            self.app_display_container,
            label_text="System Apps:",
            height=250,
            corner_radius=10
        )
        self.system_apps_scroll_frame.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")
        self.system_apps_scroll_frame.grid_columnconfigure(0, weight=1)
        self.system_apps_scroll_frame.grid_columnconfigure(1, weight=0)

        self.all_apps_categorized = {'external': [], 'system': []}

        # --- Initial Setup ---
        # Get the potential path to ADB
        adb_raw_path = self.get_tool_path("adb")

        # Now, handle if ADB was found or not
        if adb_raw_path:
            try:
                # If a path was found, then resolve it using resource_path
                self.adb_path = resource_path(adb_raw_path)
                print(f"[DEBUG] Final ADB path set to: {self.adb_path}")
            except Exception as e:  # Catch any error during resource_path conversion
                self.adb_path = None
                self.status_label.configure(text_color="red", text=f"Error: ADB path invalid. {e}")
                print(f"[ERROR] Could not set ADB path after resource_path: {e}")
        else:
            # If get_tool_path already returned None, ADB was not found.
            self.adb_path = None
            self.status_label.configure(text_color="red", text="Error: ADB not found. Check console.")
            print("\n!!! CRITICAL ERROR: ADB executable not found. !!!")
            print(
                "Please ensure ADB is installed and configured correctly (either in a 'adb' subfolder next to your script, or in your system's PATH).")

        self.populate_device_combobox()
        self.after(10000, self.populate_device_combobox)
        self.after(100, self.process_ui_queue)

    def process_ui_queue(self):
        try:
            while True:
                message = ui_update_queue.get_nowait()
                if message["type"] == "status":
                    self.status_label.configure(text_color=message["color"], text=message["text"])
                elif message["type"] == "refresh_apps":
                    selected_device = self.device_combobox.get()
                    if selected_device and selected_device != "No devices found":
                        self._fetch_and_display_apps(selected_device)
                ui_update_queue.task_done()
        except queue.Empty:
            pass
        self.after(100, self.process_ui_queue)

    def get_tool_path(self, tool_name):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        final_tool_path = None
        exe_name = f"{tool_name}.exe" if sys.platform == "win32" else tool_name

        candidate_path_specific_folder = os.path.join(script_dir, tool_name, exe_name)
        if os.path.exists(candidate_path_specific_folder) and os.path.isfile(candidate_path_specific_folder):
            final_tool_path = candidate_path_specific_folder
            print(f"[DEBUG] Trying: {final_tool_path}")

        if final_tool_path is None:
            print(f"[DEBUG] {tool_name} not found in specific folder. Checking system PATH...")
            try:
                check_cmd = ['where', tool_name] if sys.platform == "win32" else ['which', tool_name]
                result = subprocess.run(check_cmd, capture_output=True, text=True, check=False, timeout=5)
                if result.returncode == 0:
                    final_tool_path = result.stdout.strip()
                    print(f"[DEBUG] Found {tool_name} at: {final_tool_path} (in system PATH)")
                else:
                    print(f"[DEBUG] 'where'/'which' command failed for {tool_name}. Stderr: {result.stderr.strip()}")
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
                print(f"[DEBUG] Error trying 'where'/'which' for {tool_name}: {e}")

        if final_tool_path:
            try:
                print(f"[DEBUG] Verifying executability of {final_tool_path}...")
                test_cmd = [final_tool_path]
                if tool_name == "adb":
                    test_cmd.append("version")

                process = subprocess.Popen(test_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = process.communicate(timeout=5)

                print(f"[DEBUG] {tool_name} test command stdout: {stdout.decode().strip()}")
                print(f"[DEBUG] {tool_name} test command stderr: {stderr.decode().strip()}")
                print(f"[DEBUG] {tool_name} test command return code: {process.returncode}")

                if process.returncode != 0 and \
                        not (b"version" in stdout.lower() or b"usage" in stdout.lower() or b"usage" in stderr.lower()):
                    print(
                        f"Warning: {tool_name} found at {final_tool_path} but failed initial execution test. It might not be truly executable or compatible.")
                    final_tool_path = None

            except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                print(f"Warning: {tool_name} found at {final_tool_path} but failed to execute test command: {e}")
                final_tool_path = None

        if not final_tool_path:
            print(f"!!! {tool_name} not found or not executable. !!!")
            print(f"Please ensure {tool_name} is correctly installed and accessible.")

        return final_tool_path

    def get_adb_devices(self):
        if not self.adb_path:
            print("[DEBUG] ADB path is None, cannot get devices.")
            return {}

        devices = {}
        # Use self.adb_path directly as it's now guaranteed to be a string or None
        adb_command = [self.adb_path, "devices"]
        print(f"[DEBUG] Running ADB command: {' '.join(adb_command)}")
        try:
            process = subprocess.run(adb_command, capture_output=True, text=True, check=False, timeout=10)

            print(f"[DEBUG] ADB devices stdout:\n{process.stdout.strip()}")
            print(f"[DEBUG] ADB devices stderr:\n{process.stderr.strip()}")
            print(f"[DEBUG] ADB devices return code: {process.returncode}")

            if process.returncode != 0:
                print(f"Error executing 'adb devices': {process.stderr.strip()}")
                self.status_label.configure(text_color="red", text=f"ADB error: {process.stderr.strip()[:100]}...")
                return {}

            lines = process.stdout.strip().split('\n')
            if len(lines) > 1:
                for line in lines[1:]:
                    if "\tdevice" in line:
                        serial = line.split('\t')[0].strip()
                        devices[serial] = serial

            if not devices:
                print("[DEBUG] No devices found after parsing ADB output.")
                self.status_label.configure(text_color="orange", text="No ADB devices connected. Connect a device.")
            else:
                print(f"[DEBUG] Found devices: {list(devices.keys())}")
                self.status_label.configure(text_color="green", text="Devices detected!")

            return devices
        except (subprocess.TimeoutExpired) as e:
            print(f"ADB command 'devices' timed out: {e}")
            self.status_label.configure(text_color="red", text="ADB devices command timed out.")
            return {}
        except Exception as e:
            print(f"An unexpected error occurred while getting ADB devices: {e}")
            self.status_label.configure(text_color="red", text=f"Error getting devices: {e}")
            return {}

    def populate_device_combobox(self):
        devices = self.get_adb_devices()
        device_serials = list(devices.keys())
        self.device_combobox.configure(values=device_serials)

        if device_serials:
            current_selection = self.device_combobox.get()
            if not current_selection or current_selection not in device_serials:
                self.device_combobox.set(device_serials[0])
            self.on_device_selected(self.device_combobox.get())
        else:
            self.device_combobox.set("No devices found")
            self._clear_and_display_message_in_frames("Please connect an ADB device to list applications.")

    def on_device_selected(self, selected_device_serial):
        if selected_device_serial and selected_device_serial != "No devices found":
            self._fetch_and_display_apps(selected_device_serial)
        else:
            self._clear_and_display_message_in_frames("No device selected.")

    def _clear_and_display_message_in_frames(self, message):
        """Helper to clear both app frames and display a single message centrally."""
        # Clear external apps frame
        for widget in self.external_apps_scroll_frame.winfo_children():
            if isinstance(widget, customtkinter.CTkFrame) or isinstance(widget, customtkinter.CTkLabel):
                widget.destroy()
        # Clear system apps frame
        for widget in self.system_apps_scroll_frame.winfo_children():
            if isinstance(widget, customtkinter.CTkFrame) or isinstance(widget, customtkinter.CTkLabel):
                widget.destroy()

        # Display message in the external apps frame as the primary place
        message_label = customtkinter.CTkLabel(
            self.external_apps_scroll_frame,
            text=message,
            fg_color="transparent",
            text_color="gray",
            wraplength=self.app_list_wraplength + 100
        )
        message_label.grid(row=0, column=0, padx=5, pady=5, sticky="ew", columnspan=2)

    def _fetch_and_display_apps(self, device_serial):
        self._clear_and_display_message_in_frames("Loading apps... This may take a moment.")
        self.update_idletasks()

        self.all_apps_categorized = self.get_installed_apps(device_serial)

        total_apps_found = len(self.all_apps_categorized['external']) + len(self.all_apps_categorized['system'])

        if total_apps_found == 0:
            print(f"[DEBUG] No apps found for device {device_serial} (lists are empty).")
            self.status_label.configure(text_color="orange", text=f"No apps found on {device_serial}.")
        else:
            print(
                f"[DEBUG] Found {len(self.all_apps_categorized['external'])} external and {len(self.all_apps_categorized['system'])} system apps for device {device_serial}.")
            self.status_label.configure(text_color="green", text=f"Found {total_apps_found} apps.")

        self._display_filtered_apps()

    def get_installed_apps(self, device_serial):
        if not self.adb_path:
            print("[DEBUG] ADB path is None, cannot get installed apps.")
            return {'external': [], 'system': []}

        all_apps = []
        adb_command = [self.adb_path, "-s", device_serial, "shell", "pm", "list", "packages", "-f"]
        print(f"[DEBUG] Running ADB command to list ALL apps: {' '.join(adb_command)}")
        try:
            process = subprocess.run(adb_command, capture_output=True, text=True, check=False, timeout=60)

            print(f"[DEBUG] ADB list packages stdout (truncated):\n{process.stdout.strip()[:1000]}...")
            print(f"[DEBUG] ADB list packages stderr:\n{process.stderr.strip()}")
            print(f"[DEBUG] ADB list packages return code: {process.returncode}")

            if process.returncode != 0:
                print(f"Error executing 'adb pm list packages': {process.stderr.strip()}")
                self.status_label.configure(text_color="red",
                                            text=f"ADB app list error: {process.stderr.strip()[:100]}...")
                return {'external': [], 'system': []}

            for line in process.stdout.splitlines():
                if line.startswith("package:"):
                    parts = line.strip().split("=", 1)
                    if len(parts) == 2:
                        apk_path_full = parts[0].replace("package:", "")
                        package_name = parts[1]
                        all_apps.append({'package_name': package_name, 'apk_path': apk_path_full})

            external_apps = []
            system_apps = []
            for app in all_apps:
                if app['apk_path'].startswith('/system/app/') or \
                        app['apk_path'].startswith('/system/priv-app/') or \
                        app['apk_path'].startswith('/vendor/app/') or \
                        app['apk_path'].startswith('/product/app/') or \
                        app['apk_path'].startswith('/data/app/~~/'):
                    system_apps.append(app)
                else:
                    external_apps.append(app)

            print(
                f"[DEBUG] get_installed_apps returning {len(external_apps)} external and {len(system_apps)} system apps.")
            return {'external': external_apps, 'system': system_apps}

        except (subprocess.TimeoutExpired) as e:
            print(f"ADB command 'list packages' timed out: {e}")
            self.status_label.configure(text_color="red", text="ADB app list command timed out.")
            return {'external': [], 'system': []}
        except Exception as e:
            print(f"An unexpected error occurred while getting installed apps: {e}")
            self.status_label.configure(text_color="red", text=f"Error getting app list: {e}")
            return {'external': [], 'system': []}

    def on_search_change(self, event=None):
        self._display_filtered_apps()

    def _display_filtered_apps(self):
        # Clear both scrollable frames
        for widget in self.external_apps_scroll_frame.winfo_children():
            if isinstance(widget, customtkinter.CTkFrame) or isinstance(widget, customtkinter.CTkLabel):
                widget.destroy()
        for widget in self.system_apps_scroll_frame.winfo_children():
            if isinstance(widget, customtkinter.CTkFrame) or isinstance(widget, customtkinter.CTkLabel):
                widget.destroy()

        search_query = self.search_entry.get().lower().strip()

        external_apps_to_display = []
        system_apps_to_display = []

        # Filter external apps
        if search_query:
            for app_info in self.all_apps_categorized.get('external', []):
                if search_query in app_info['package_name'].lower():
                    external_apps_to_display.append(app_info)
        else:
            external_apps_to_display = list(self.all_apps_categorized.get('external', []))

        # Filter system apps
        if search_query:
            for app_info in self.all_apps_categorized.get('system', []):
                if search_query in app_info['package_name'].lower():
                    system_apps_to_display.append(app_info)
        else:
            system_apps_to_display = list(self.all_apps_categorized.get('system', []))

        # Sort filtered lists
        external_apps_to_display.sort(key=lambda x: x['package_name'].lower())
        system_apps_to_display.sort(key=lambda x: x['package_name'].lower())

        # Populate External Apps Frame
        if external_apps_to_display:
            for i, app_info in enumerate(external_apps_to_display):
                app_frame = customtkinter.CTkFrame(
                    self.external_apps_scroll_frame,
                    fg_color="gray75" if i % 2 == 0 else "gray80",
                    corner_radius=6
                )
                app_frame.grid(row=i, column=0, padx=5, pady=3, sticky="ew", columnspan=2)

                app_frame.grid_columnconfigure(0, weight=1)
                app_frame.grid_columnconfigure(1, weight=0)

                app_name_package_text = f"Package: {app_info['package_name']}\nPath: {app_info['apk_path']}"
                app_label = customtkinter.CTkLabel(
                    app_frame,
                    text=app_name_package_text,
                    text_color="black",
                    justify="left",
                    anchor="w",
                    wraplength=self.app_list_wraplength
                )
                app_label.grid(row=0, column=0, padx=(10, 5), pady=5, sticky="ew")

                delete_button = customtkinter.CTkButton(
                    app_frame,
                    text="Delete",
                    fg_color="red",
                    hover_color="darkred",
                    command=lambda pkg=app_info['package_name']: self.confirm_and_delete_app(pkg)
                )
                delete_button.grid(row=0, column=1, padx=(5, 10), pady=5, sticky="e")
        else:
            message_text = "No matching external apps found." if search_query else "No external apps found."
            message_label = customtkinter.CTkLabel(
                self.external_apps_scroll_frame,
                text=message_text,
                fg_color="transparent",
                text_color="gray",
                wraplength=self.app_list_wraplength + 50
            )
            message_label.grid(row=0, column=0, padx=5, pady=5, sticky="ew", columnspan=2)

        # Populate System Apps Frame
        if system_apps_to_display:
            for i, app_info in enumerate(system_apps_to_display):
                app_frame = customtkinter.CTkFrame(
                    self.system_apps_scroll_frame,
                    fg_color="gray75" if i % 2 == 0 else "gray80",
                    corner_radius=6
                )
                app_frame.grid(row=i, column=0, padx=5, pady=3, sticky="ew", columnspan=2)

                app_frame.grid_columnconfigure(0, weight=1)
                app_frame.grid_columnconfigure(1, weight=0)

                app_name_package_text = f"Package: {app_info['package_name']}\nPath: {app_info['apk_path']}"
                app_label = customtkinter.CTkLabel(
                    app_frame,
                    text=app_name_package_text,
                    text_color="black",
                    justify="left",
                    anchor="w",
                    wraplength=self.app_list_wraplength
                )
                app_label.grid(row=0, column=0, padx=(10, 5), pady=5, sticky="ew")

                delete_button = customtkinter.CTkButton(
                    app_frame,
                    text="Delete",
                    fg_color="gray",
                    hover_color="darkred",
                    command=lambda pkg=app_info['package_name']: self.confirm_and_delete_app(pkg)
                )
                delete_button.grid(row=0, column=1, padx=(5, 10), pady=5, sticky="e")
        else:
            message_text = "No matching system apps found." if search_query else "No system apps found."
            message_label = customtkinter.CTkLabel(
                self.system_apps_scroll_frame,
                text=message_text,
                fg_color="transparent",
                text_color="gray",
                wraplength=self.app_list_wraplength + 50
            )
            message_label.grid(row=0, column=0, padx=5, pady=5, sticky="ew", columnspan=2)

    def confirm_and_delete_app(self, package_name):
        dialog = customtkinter.CTkToplevel(self)
        dialog.title("Confirm Deletion")
        dialog.geometry("350x150")
        dialog.transient(self)
        dialog.grab_set()

        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

        message_label = customtkinter.CTkLabel(
            dialog,
            text=f"Are you sure you want to delete:\n{package_name}?",
            wraplength=300
        )
        message_label.pack(pady=20)

        button_frame = customtkinter.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=10)
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        yes_button = customtkinter.CTkButton(
            button_frame,
            text="Yes, Delete It",
            fg_color="red",
            hover_color="darkred",
            command=lambda: self.execute_delete_app_in_thread(package_name, dialog)
        )
        yes_button.grid(row=0, column=0, padx=10)

        no_button = customtkinter.CTkButton(
            button_frame,
            text="No, Keep It",
            command=dialog.destroy
        )
        no_button.grid(row=0, column=1, padx=10)

    def execute_delete_app_in_thread(self, package_name_raw, dialog):
        dialog.destroy()

        true_package_name = package_name_raw
        if '=' in package_name_raw:
            true_package_name = package_name_raw.split('=')[-1]

        print(
            f"[DEBUG_BACKGROUND] Received raw for uninstall: '{package_name_raw}', Parsed for uninstall: '{true_package_name}'")

        self.status_label.configure(text_color="orange", text=f"Deleting {true_package_name}...")

        delete_thread = threading.Thread(target=self._delete_app_background, args=(true_package_name,))
        delete_thread.daemon = True
        delete_thread.start()

    def _delete_app_background(self, package_name):
        selected_device_serial = self.device_combobox.get()
        if not selected_device_serial or selected_device_serial == "No devices found":
            ui_update_queue.put({"type": "status", "text": "No device selected for deletion.", "color": "red"})
            return

        if not self.adb_path:
            ui_update_queue.put({"type": "status", "text": "ADB not found. Cannot delete.", "color": "red"})
            return

        try:
            print(f"[DEBUG_BACKGROUND] Attempting to uninstall {package_name} from {selected_device_serial}...")
            command = [self.adb_path, "-s", selected_device_serial, "uninstall", package_name]
            process = subprocess.run(command, capture_output=True, text=True, check=False, timeout=60)

            print(f"[DEBUG_BACKGROUND] Uninstall stdout:\n{process.stdout.strip()}")
            print(f"[DEBUG_BACKGROUND] Uninstall stderr:\n{process.stderr.strip()}")
            print(f"[DEBUG_BACKGROUND] Uninstall return code: {process.returncode}")

            if process.returncode == 0 and "Success" in process.stdout:
                ui_update_queue.put(
                    {"type": "status", "text": f"Successfully deleted {package_name}!", "color": "green"})
                ui_update_queue.put({"type": "refresh_apps"})
                print(f"Uninstallation successful for {package_name}.")
            else:
                error_message = process.stderr.strip() if process.stderr else process.stdout.strip() if process.stdout else "Unknown error."
                if not error_message: error_message = "Failed with no specific output."
                ui_update_queue.put(
                    {"type": "status", "text": f"Failed to delete {package_name}: {error_message[:100]}...",
                     "color": "red"})
                print(
                    f"Uninstallation failed for {package_name}. Full Stderr: {process.stderr}, Full Stdout: {process.stdout}")

        except (subprocess.TimeoutExpired) as e:
            ui_update_queue.put(
                {"type": "status", "text": f"Error deleting {package_name}: Command timed out.", "color": "red"})
            print(f"Error during uninstall command for {package_name}: {e}")
        except Exception as e:
            ui_update_queue.put(
                {"type": "status", "text": f"An unexpected error occurred during deletion: {e}", "color": "red"})
            print(f"An unexpected error occurred during uninstallation of {package_name}: {e}")

    # --- about_me function ---
    def about_me(self):
        """
        Displays an informational message box about the application.
        """
        print(f"[DEBUG_ABOUT_ME] Type of CTkMessageBox: {type(CTkMessageBox)}")
        import inspect
        try:
            print(f"[DEBUG_ABOUT_ME] Signature of CTkMessageBox.__init__: {inspect.signature(CTkMessageBox.__init__)}")
        except AttributeError:
            print(
                "[DEBUG_ABOUT_ME] CTkMessageBox.__init__ has no signature attribute, possibly not a class or misdefined.")

        app_info_message = (
            "ADB App Manager\n\n"
            "Version: 1.0\n"
            "Developed by: Your mApp586\n\n"
            "This application allows you to list and manage\n"
            "both external (user-installed) and system applications\n"
            "on your connected Android device via ADB.\n\n"
            "Note: Deleting system apps may require a rooted device\n"
            "and can potentially cause instability. Proceed with caution."
        )
        try:
            CTkMessageBox(
                self,
                title="About ADB App Manager",
                message=app_info_message,
                icon_type="info",
                width=450,
                height=280
            )
        except TypeError as e:
            print(f"[ERROR] TypeError when calling CTkMessageBox in about_me: {e}")
            print("This often means there's a conflict in the CTkMessageBox definition or how it's imported.")
            print(
                "Please ensure you are running the latest version of the script and try restarting your Python environment/IDE.")
        except Exception as e:
            print(f"[ERROR] An unexpected error occurred in about_me: {e}")


if __name__ == "__main__":
    customtkinter.set_appearance_mode("System")
    customtkinter.set_default_color_theme("blue")

    app = App()
    app.mainloop()
