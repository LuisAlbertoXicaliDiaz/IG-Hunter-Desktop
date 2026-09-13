from __future__ import annotations

import customtkinter as ctk

from styles import COLORS, FONTS, PADDING


class ManualWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Manual de uso")
        self.geometry("720x580")
        self.minsize(620, 500)
        self.configure(fg_color=COLORS["bg"])
        self.transient(master)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 12))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Cómo usar IgHunter Pro",
            font=FONTS["title"],
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Analiza tus archivos exportados de Instagram sin iniciar sesión ni pedir contraseña.",
            font=FONTS["subtitle"],
            text_color=COLORS["muted"],
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=COLORS["surface"],
            corner_radius=10,
            border_width=1,
            border_color=COLORS["border"],
        )
        scroll.grid(row=1, column=0, sticky="nsew", padx=24, pady=12)
        scroll.grid_columnconfigure(0, weight=1)

        steps = [
            (
                "1. Descarga tus datos",
                "En Instagram entra a Centro de cuentas > Tu información y permisos > Descargar tu información.",
            ),
            (
                "2. Carga la carpeta completa",
                "Si tienes varios archivos como followers_1.html, following.html, close_friends.html o pending_follow_requests.html, selecciona la carpeta y la app los detectará.",
            ),
            (
                "3. Revisa los perfiles",
                "Cada usuario aparece en una tarjeta con botones para abrir el perfil, copiar el link o copiar el usuario.",
            ),
            (
                "4. Usa las pestañas",
                "Puedes revisar quién no te sigue, quién te sigue y tú no sigues, mutuos, mejores amigos, favoritos, solicitudes pendientes y más.",
            ),
            (
                "5. Exporta tu reporte",
                "Puedes guardar el resultado como TXT, CSV o Excel. Todos incluyen el enlace directo al perfil.",
            ),
            (
                "Privacidad",
                "Todo se procesa localmente en tu computadora. La app no se conecta a Instagram ni envía tus archivos a internet.",
            ),
        ]

        for index, (title, description) in enumerate(steps):
            card = ctk.CTkFrame(
                scroll,
                fg_color=COLORS["surface_2"],
                corner_radius=8,
                border_width=1,
                border_color=COLORS["border"],
            )
            card.grid(row=index, column=0, sticky="ew", padx=12, pady=8)
            card.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                card,
                text=title,
                font=FONTS["section"],
                text_color=COLORS["text"],
            ).grid(row=0, column=0, sticky="w", padx=PADDING["card"], pady=(12, 2))
            ctk.CTkLabel(
                card,
                text=description,
                font=FONTS["body"],
                text_color=COLORS["muted"],
                wraplength=620,
                justify="left",
            ).grid(row=1, column=0, sticky="w", padx=PADDING["card"], pady=(0, 12))

        ctk.CTkButton(
            self,
            text="Entendido",
            command=self.destroy,
            height=42,
            font=FONTS["button"],
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
        ).grid(row=2, column=0, sticky="e", padx=24, pady=(8, 22))
