from __future__ import annotations

import threading
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from logic import (
    CATEGORY_LABELS,
    AnalysisResult,
    analyze_instagram_data,
    export_result,
    profile_url,
    scan_instagram_export,
)
from manual import ManualWindow
from styles import APP_NAME, APP_SIZE, COLORS, FONTS, MIN_SIZE, PADDING, THEME_COLOR, THEME_MODE


MAX_RENDERED_USERS = 350


class IgHunterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode(THEME_MODE)
        ctk.set_default_color_theme(THEME_COLOR)

        self.title(APP_NAME)
        self.geometry(APP_SIZE)
        self.minsize(*MIN_SIZE)
        self.configure(fg_color=COLORS["bg"])

        self.followers_path = ctk.StringVar()
        self.following_path = ctk.StringVar()
        self.search_text = ctk.StringVar()
        self.status_text = ctk.StringVar(value="Selecciona tu carpeta exportada de Instagram.")
        self.detected_text = ctk.StringVar(value="Aún no se han detectado archivos.")

        self.result: AnalysisResult | None = None
        self.extra_paths: dict[str, Path] = {}
        self.current_category = "not_following_back"
        self.loading = False
        self.loading_tick = 0

        self.tab_map = {
            "No te siguen": "not_following_back",
            "Te siguen": "fans",
            "Mutuos": "mutuals",
            "Mejores amigos": "close_friends",
            "Pendientes": "pending_follow_requests",
            "Favoritos": "favorited_profiles",
            "Solicitudes": "recent_follow_requests",
            "Dejados de seguir": "recently_unfollowed_profiles",
            "Sugerencias": "removed_suggestions",
        }

        self._build_layout()
        self._animate_status()

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(
            self,
            width=350,
            corner_radius=0,
            fg_color=COLORS["surface"],
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color=COLORS["bg"])
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(3, weight=1)

        self._build_sidebar()
        self._build_content()

    def _build_sidebar(self) -> None:
        self.sidebar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.sidebar,
            text=APP_NAME,
            font=FONTS["title"],
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(26, 4))

        ctk.CTkLabel(
            self.sidebar,
            text="Panel profesional para revisar seguidores, links y listas exportadas.",
            font=FONTS["subtitle"],
            text_color=COLORS["muted"],
            wraplength=292,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=22, pady=(0, 18))

        ctk.CTkButton(
            self.sidebar,
            text="Cargar carpeta completa",
            height=44,
            font=FONTS["button"],
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            command=self._select_export_folder,
        ).grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 10))

        self._file_card(
            row=3,
            title="followers / followers_1",
            variable=self.followers_path,
            command=lambda: self._select_path(self.followers_path),
        )
        self._file_card(
            row=4,
            title="following",
            variable=self.following_path,
            command=lambda: self._select_path(self.following_path),
        )

        detected_card = ctk.CTkFrame(
            self.sidebar,
            fg_color=COLORS["surface_2"],
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border"],
        )
        detected_card.grid(row=5, column=0, sticky="ew", padx=22, pady=8)
        detected_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            detected_card,
            text="Archivos extra detectados",
            font=FONTS["body"],
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 2))
        ctk.CTkLabel(
            detected_card,
            textvariable=self.detected_text,
            font=FONTS["small"],
            text_color=COLORS["muted"],
            wraplength=286,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 12))

        self.analyze_button = ctk.CTkButton(
            self.sidebar,
            text="Iniciar análisis",
            height=46,
            font=FONTS["button"],
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            command=self._start_analysis,
        )
        self.analyze_button.grid(row=6, column=0, sticky="ew", padx=22, pady=(14, 8))

        ctk.CTkButton(
            self.sidebar,
            text="Manual de uso",
            height=40,
            font=FONTS["button"],
            fg_color=COLORS["surface_2"],
            hover_color=COLORS["border"],
            command=self._open_manual,
        ).grid(row=7, column=0, sticky="ew", padx=22, pady=(0, 14))

        self.progress = ctk.CTkProgressBar(self.sidebar, mode="indeterminate")
        self.progress.grid(row=8, column=0, sticky="ew", padx=22, pady=(0, 8))
        self.progress.stop()
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(
            self.sidebar,
            textvariable=self.status_text,
            font=FONTS["small"],
            text_color=COLORS["muted"],
            wraplength=292,
            justify="left",
        )
        self.status_label.grid(row=9, column=0, sticky="w", padx=22, pady=(0, 18))

        self.sidebar.grid_rowconfigure(10, weight=1)

        ctk.CTkLabel(
            self.sidebar,
            text="Privacidad: todo se analiza localmente. La app solo abre perfiles en tu navegador.",
            font=FONTS["small"],
            text_color=COLORS["muted"],
            wraplength=292,
            justify="left",
        ).grid(row=11, column=0, sticky="w", padx=22, pady=(0, 24))

    def _file_card(self, row: int, title: str, variable: ctk.StringVar, command) -> None:
        card = ctk.CTkFrame(
            self.sidebar,
            fg_color=COLORS["surface_2"],
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border"],
        )
        card.grid(row=row, column=0, sticky="ew", padx=22, pady=7)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text=title,
            font=FONTS["body"],
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 4))

        ctk.CTkEntry(
            card,
            textvariable=variable,
            height=34,
            font=FONTS["small"],
            fg_color=COLORS["bg"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            placeholder_text="Selecciona HTML, JSON o carpeta",
        ).grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))

        ctk.CTkButton(
            card,
            text="Seleccionar archivo",
            height=32,
            font=FONTS["button"],
            fg_color=COLORS["surface"],
            hover_color=COLORS["border"],
            command=command,
        ).grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 14))

    def _build_content(self) -> None:
        header = ctk.CTkFrame(self.content, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=PADDING["page"], pady=(24, 12))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Dashboard de Instagram",
            font=FONTS["title"],
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Abre perfiles, copia enlaces, filtra usuarios y exporta reportes completos.",
            font=FONTS["subtitle"],
            text_color=COLORS["muted"],
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        self.stats_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.stats_frame.grid(row=1, column=0, sticky="ew", padx=PADDING["page"], pady=(0, 12))
        for col in range(5):
            self.stats_frame.grid_columnconfigure(col, weight=1, uniform="stats")

        self.stat_labels = {
            "followers": self._stat_card(0, "Seguidores", "0", COLORS["primary"]),
            "following": self._stat_card(1, "Seguidos", "0", COLORS["warning"]),
            "not_back": self._stat_card(2, "No te siguen", "0", COLORS["danger"]),
            "fans": self._stat_card(3, "Fans", "0", COLORS["success"]),
            "extras": self._stat_card(4, "Listas extra", "0", COLORS["muted"]),
        }

        toolbar = ctk.CTkFrame(self.content, fg_color="transparent")
        toolbar.grid(row=2, column=0, sticky="ew", padx=PADDING["page"], pady=(0, 12))
        toolbar.grid_columnconfigure(0, weight=1)

        ctk.CTkEntry(
            toolbar,
            textvariable=self.search_text,
            height=40,
            font=FONTS["body"],
            fg_color=COLORS["surface"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            placeholder_text="Buscar usuario...",
        ).grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.search_text.trace_add("write", lambda *_: self._render_results())

        actions = [
            ("Abrir visible", self._open_first_visible),
            ("Copiar visible", self._copy_visible_links),
            ("TXT", lambda: self._export("txt")),
            ("CSV", lambda: self._export("csv")),
            ("Excel", lambda: self._export("xlsx")),
        ]
        for index, (label, command) in enumerate(actions):
            ctk.CTkButton(
                toolbar,
                text=label,
                height=40,
                width=104,
                font=FONTS["button"],
                fg_color=COLORS["surface_2"],
                hover_color=COLORS["border"],
                command=command,
            ).grid(row=0, column=index + 1, padx=(0, 8 if index < len(actions) - 1 else 0))

        self.tabs = ctk.CTkTabview(
            self.content,
            fg_color=COLORS["surface"],
            segmented_button_fg_color=COLORS["surface_2"],
            segmented_button_selected_color=COLORS["primary"],
            segmented_button_selected_hover_color=COLORS["primary_hover"],
            segmented_button_unselected_color=COLORS["surface_2"],
            segmented_button_unselected_hover_color=COLORS["border"],
            text_color=COLORS["text"],
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border"],
            command=self._on_tab_change,
        )
        self.tabs.grid(row=3, column=0, sticky="nsew", padx=PADDING["page"], pady=(0, 24))

        self.result_frames: dict[str, ctk.CTkScrollableFrame] = {}

        for tab_name, category in self.tab_map.items():
            tab = self.tabs.add(tab_name)
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)
            scroll = ctk.CTkScrollableFrame(tab, fg_color=COLORS["bg"], corner_radius=8)
            scroll.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
            scroll.grid_columnconfigure(0, weight=1)
            self.result_frames[category] = scroll

        self._render_empty_state()

    def _stat_card(self, column: int, title: str, value: str, accent: str) -> ctk.CTkLabel:
        card = ctk.CTkFrame(
            self.stats_frame,
            fg_color=COLORS["surface"],
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border"],
        )
        card.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 8, 0))
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text=title,
            font=FONTS["small"],
            text_color=COLORS["muted"],
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 0))

        label = ctk.CTkLabel(card, text=value, font=("Segoe UI", 25, "bold"), text_color=accent)
        label.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 12))
        return label

    def _select_export_folder(self) -> None:
        folder_path = filedialog.askdirectory(title="Seleccionar carpeta exportada de Instagram")
        if not folder_path:
            return

        try:
            detected = scan_instagram_export(folder_path)
        except Exception as error:
            messagebox.showerror("Error", str(error))
            return

        if "followers" in detected:
            self.followers_path.set(str(detected["followers"]))
        if "following" in detected:
            self.following_path.set(str(detected["following"]))

        self.extra_paths = {
            category: path
            for category, path in detected.items()
            if category not in {"followers", "following"}
        }
        self._update_detected_text(detected)
        self.status_text.set("Carpeta cargada. Presiona Iniciar análisis.")

    def _update_detected_text(self, detected: dict[str, Path]) -> None:
        if not detected:
            self.detected_text.set("No se detectaron archivos conocidos.")
            return

        lines = []
        for category, path in detected.items():
            label = CATEGORY_LABELS.get(category, category)
            lines.append(f"{label}: {path.name}")
        self.detected_text.set("\n".join(lines))

    def _select_path(self, target: ctk.StringVar) -> None:
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo de Instagram",
            filetypes=[
                ("Archivos de Instagram", "*.html *.htm *.json"),
                ("HTML", "*.html *.htm"),
                ("JSON", "*.json"),
                ("Todos los archivos", "*.*"),
            ],
        )
        if file_path:
            target.set(file_path)
            return

        folder_path = filedialog.askdirectory(title="O seleccionar carpeta")
        if folder_path:
            target.set(folder_path)

    def _start_analysis(self) -> None:
        followers = self.followers_path.get().strip()
        following = self.following_path.get().strip()

        if not followers or not following:
            messagebox.showwarning(
                "Faltan archivos",
                "Selecciona la carpeta completa o carga followers y following manualmente.",
            )
            return

        self._set_loading(True, "Analizando archivos")
        thread = threading.Thread(
            target=self._run_analysis,
            args=(followers, following, dict(self.extra_paths)),
            daemon=True,
        )
        thread.start()

    def _run_analysis(self, followers: str, following: str, extra_paths: dict[str, Path]) -> None:
        try:
            result = analyze_instagram_data(followers, following, extra_paths)
        except Exception as error:
            self.after(0, lambda: self._show_error(error))
            return

        self.after(0, lambda: self._show_result(result))

    def _show_result(self, result: AnalysisResult) -> None:
        self.result = result
        self._set_loading(
            False,
            f"Análisis completado: {result.not_following_back_count} usuarios no te siguen.",
        )

        extra_total = sum(len(users) for users in result.extra_categories.values())
        self.stat_labels["followers"].configure(text=str(result.followers_count))
        self.stat_labels["following"].configure(text=str(result.following_count))
        self.stat_labels["not_back"].configure(text=str(result.not_following_back_count))
        self.stat_labels["fans"].configure(text=str(result.fans_count))
        self.stat_labels["extras"].configure(text=str(extra_total))
        self._render_results()

    def _show_error(self, error: Exception) -> None:
        self._set_loading(False, "No se pudo completar el análisis.")
        messagebox.showerror("Error", str(error))

    def _set_loading(self, is_loading: bool, status: str) -> None:
        self.loading = is_loading
        self.status_text.set(status)
        self.analyze_button.configure(state="disabled" if is_loading else "normal")
        if is_loading:
            self.progress.start()
        else:
            self.progress.stop()
            self.progress.set(0)

    def _animate_status(self) -> None:
        if self.loading:
            self.loading_tick = (self.loading_tick + 1) % 4
            base = self.status_text.get().rstrip(".")
            self.status_text.set(f"{base}{'.' * self.loading_tick}")
        self.after(450, self._animate_status)

    def _on_tab_change(self) -> None:
        selected_tab = self.tabs.get()
        self.current_category = self.tab_map.get(selected_tab, "not_following_back")
        self._render_results()

    def _render_empty_state(self) -> None:
        for category, frame in self.result_frames.items():
            self._clear_frame(frame)
            ctk.CTkLabel(
                frame,
                text="Carga tus archivos y ejecuta el análisis para ver los perfiles aquí.",
                font=FONTS["body"],
                text_color=COLORS["muted"],
                wraplength=620,
                justify="left",
            ).grid(row=0, column=0, sticky="w", padx=14, pady=16)

    def _render_results(self) -> None:
        if not self.result:
            return

        for category, frame in self.result_frames.items():
            self._clear_frame(frame)
            visible_users = self._visible_users(category)

            if not visible_users:
                ctk.CTkLabel(
                    frame,
                    text="No hay usuarios para mostrar en esta categoría.",
                    font=FONTS["body"],
                    text_color=COLORS["muted"],
                ).grid(row=0, column=0, sticky="w", padx=14, pady=16)
                continue

            shown_users = visible_users[:MAX_RENDERED_USERS]
            for row, username in enumerate(shown_users):
                self._profile_card(frame, row, username, category)

            if len(visible_users) > MAX_RENDERED_USERS:
                ctk.CTkLabel(
                    frame,
                    text=(
                        f"Mostrando {MAX_RENDERED_USERS} de {len(visible_users)} usuarios. "
                        "Usa el buscador o exporta el reporte para ver todos."
                    ),
                    font=FONTS["small"],
                    text_color=COLORS["muted"],
                    wraplength=700,
                    justify="left",
                ).grid(row=len(shown_users), column=0, sticky="ew", padx=14, pady=14)

    def _profile_card(self, parent, row: int, username: str, category: str) -> None:
        url = profile_url(username)
        card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["surface"],
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border"],
        )
        card.grid(row=row, column=0, sticky="ew", padx=8, pady=6)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text=f"@{username}",
            font=FONTS["section"],
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 0))

        ctk.CTkLabel(
            card,
            text=url,
            font=FONTS["small"],
            text_color=COLORS["muted"],
        ).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 12))

        open_text = "Abrir para dejar de seguir" if category == "not_following_back" else "Abrir perfil"
        ctk.CTkButton(
            card,
            text=open_text,
            height=34,
            width=160,
            font=FONTS["button"],
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            command=lambda link=url: self._open_url(link),
        ).grid(row=0, column=1, rowspan=2, sticky="e", padx=(8, 6), pady=12)

        ctk.CTkButton(
            card,
            text="Copiar link",
            height=34,
            width=112,
            font=FONTS["button"],
            fg_color=COLORS["surface_2"],
            hover_color=COLORS["border"],
            command=lambda link=url: self._copy_to_clipboard(link, "Link copiado."),
        ).grid(row=0, column=2, rowspan=2, sticky="e", padx=6, pady=12)

        ctk.CTkButton(
            card,
            text="Copiar usuario",
            height=34,
            width=124,
            font=FONTS["button"],
            fg_color=COLORS["surface_2"],
            hover_color=COLORS["border"],
            command=lambda user=username: self._copy_to_clipboard(f"@{user}", "Usuario copiado."),
        ).grid(row=0, column=3, rowspan=2, sticky="e", padx=(6, 14), pady=12)

    def _visible_users(self, category: str) -> list[str]:
        if not self.result:
            return []

        query = self.search_text.get().strip().lower()
        users = self.result.category_users(category)
        if not query:
            return users
        return [user for user in users if query in user.lower()]

    def _open_url(self, url: str) -> None:
        webbrowser.open(url)

    def _copy_to_clipboard(self, text: str, status: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status_text.set(status)

    def _open_first_visible(self) -> None:
        users = self._visible_users(self.current_category)
        if not users:
            messagebox.showinfo("Sin usuarios", "No hay usuarios visibles para abrir.")
            return
        self._open_url(profile_url(users[0]))

    def _copy_visible_links(self) -> None:
        users = self._visible_users(self.current_category)
        if not users:
            messagebox.showinfo("Sin usuarios", "No hay usuarios visibles para copiar.")
            return
        links = "\n".join(profile_url(user) for user in users)
        self._copy_to_clipboard(links, f"Se copiaron {len(users)} links visibles.")

    def _export(self, export_type: str) -> None:
        if not self.result:
            messagebox.showinfo("Sin resultados", "Primero ejecuta un análisis.")
            return

        extensions = {
            "txt": ".txt",
            "csv": ".csv",
            "xlsx": ".xlsx",
        }
        labels = {
            "txt": "TXT",
            "csv": "CSV",
            "xlsx": "Excel",
        }
        file_path = filedialog.asksaveasfilename(
            title="Guardar reporte",
            defaultextension=extensions[export_type],
            initialfile=f"Reporte_IgHunter_Pro{extensions[export_type]}",
            filetypes=[(labels[export_type], f"*{extensions[export_type]}")],
        )
        if not file_path:
            return

        output = export_result(self.result, file_path, export_type)  # type: ignore[arg-type]
        messagebox.showinfo("Reporte guardado", f"Se guardó el reporte en:\n{Path(output)}")

    def _clear_frame(self, frame) -> None:
        for widget in frame.winfo_children():
            widget.destroy()

    def _open_manual(self) -> None:
        ManualWindow(self)


if __name__ == "__main__":
    app = IgHunterApp()
    app.mainloop()
