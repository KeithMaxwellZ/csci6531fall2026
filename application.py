import json
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from client import BaseClient
from payload import Payload


WINDOW_TITLE = "Encrypted Messenger"
ROUTER_PLACEHOLDER = "http://127.0.0.1:8765/"

SERVER_ADDR = "http://127.0.0.1:9961/"


class MessengerApp:
    """Desktop shell for the messenger while the relay is still in progress."""

    def __init__(self, root):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry("1100x800")
        self.root.minsize(900, 760)
        self.root.configure(bg="#101820")

        self.client = BaseClient(ROUTER_PLACEHOLDER).start()
        self.username = ""
        self.current_contact = None
        self.received_payload_index = 0
        self.session_contacts = set()
        self.messages = {}

        self._configure_styles()
        self.show_login()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(250, self._poll_received_messages)

    

    # ===================================================
    # UI/UX functions
    # ===================================================

    def _configure_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TButton", font=("Segoe UI", 10), padding=(14, 8))
        style.configure("Accent.TButton", background="#2dd4bf", foreground="#08151b", padding=(14, 14))
        style.map("Accent.TButton", background=[("active", "#5eead4")])
        style.configure("TEntry", fieldbackground="#182631", foreground="#f4f7f8")
        style.configure("TNotebook", background="#101820", borderwidth=0)
        style.configure("TNotebook.Tab", background="#182631", foreground="#a9bbc3", padding=(16, 9))
        style.map("TNotebook.Tab", background=[("selected", "#243642")], foreground=[("selected", "#ffffff")])

    def _clear(self):
        for child in self.root.winfo_children():
            child.destroy()

    def _transition(self, callback):
        """Fade the new scene panel in without dimming the whole window."""
        steps = 7
        callback()
        target = getattr(self, "transition_target", None)
        if target is None or not target.winfo_exists():
            return

        self.root.update_idletasks()
        overlay = tk.Toplevel(self.root)
        overlay.overrideredirect(True)
        overlay.configure(bg="#101820")
        overlay.attributes("-alpha", 0.55)
        overlay.geometry(
            f"{target.winfo_width()}x{target.winfo_height()}+"
            f"{target.winfo_rootx()}+{target.winfo_rooty()}"
        )
        overlay.lift()

        def fade_in(step):
            alpha = 0.55 * (step / steps)
            overlay.attributes("-alpha", alpha)
            if step > 0:
                self.root.after(35, fade_in, step - 1)
            else:
                overlay.destroy()

        fade_in(steps)

    def _label(self, parent, text, size=10, color="#a9bbc3", **kwargs):
        return tk.Label(parent, text=text, font=("Segoe UI", size), fg=color, bg=parent["bg"], **kwargs)

    def show_login(self):
        self.username = ""
        self.current_contact = None
        self.session_contacts = set()
        self.received_payload_index = 0
        self.messages = {}
        self._clear()
        page = tk.Frame(self.root, bg="#101820")
        page.pack(fill="both", expand=True)

        panel = tk.Frame(page, bg="#182631", padx=46, pady=42)
        panel.place(relx=0.5, rely=0.5, anchor="center", width=430, height=700)
        self.transition_target = panel
        self._label(panel, "ENCRYPTED MESSENGER", 11, "#2dd4bf").pack(anchor="w")
        self._label(panel, "Private by design.", 27, "#f4f7f8").pack(anchor="w", pady=(20, 6))
        self._label(panel, "A local client node is ready. Sign in to open your secure workspace.", 10, "#a9bbc3", wraplength=330, justify="left").pack(anchor="w", pady=(0, 28))

        self._label(panel, "USERNAME", 9, "#7f9aa5").pack(anchor="w")
        username = tk.Entry(panel, bg="#101820", fg="#f4f7f8", insertbackground="#2dd4bf", relief="flat", font=("Segoe UI", 11))
        username.pack(fill="x", ipady=10, pady=(6, 18))
        self.username_entry = username
        self._label(panel, "PASSWORD", 9, "#7f9aa5").pack(anchor="w")
        password = tk.Entry(panel, show="*", bg="#101820", fg="#f4f7f8", insertbackground="#2dd4bf", relief="flat", font=("Segoe UI", 11))
        password.pack(fill="x", ipady=10, pady=(6, 24))
        self._label(panel, "ROUTER ADDRESS", 9, "#7f9aa5").pack(anchor="w")
        router_address = tk.Entry(panel, bg="#101820", fg="#f4f7f8", insertbackground="#2dd4bf", relief="flat", font=("Segoe UI", 10))
        router_address.pack(fill="x", ipady=10, pady=(6, 18))
        router_address.insert(0, ROUTER_PLACEHOLDER)

        ttk.Button(panel, text="Sign in", style="Accent.TButton", command=lambda: self._handle_login(username.get(), password.get(), router_address.get())).pack(fill="x")
        ttk.Button(panel, text="Create account", command=lambda: self._prompt_registration(username.get(), password.get(), router_address.get())).pack(fill="x", pady=(10, 0))
        self._label(panel, "TLS session  •  Argon2id password storage", 9, "#6d8792").pack(anchor="w", pady=(28, 0))

    def show_chat(self):
        self._clear()
        header = tk.Frame(self.root, bg="#182631", height=72)
        header.pack(fill="x")
        header.pack_propagate(False)
        self._label(header, "ENCRYPTED MESSENGER", 11, "#2dd4bf").pack(side="left", padx=28)
        self._label(header, f"{self.username}  |  client online", 10, "#a9bbc3").pack(side="left", padx=12)
        ttk.Button(header, text="Admin view", command=lambda: self._transition(self.show_admin)).pack(side="right", padx=(0, 10), pady=16)
        ttk.Button(header, text="Log out", command=lambda: self._transition(self.show_login)).pack(side="right", padx=22, pady=16)

        body = tk.Frame(self.root, bg="#101820")
        body.pack(fill="both", expand=True, padx=24, pady=24)
        self.transition_target = body
        self._build_contacts(body)
        self._build_conversation(body)

    def _build_contacts(self, parent):
        contacts = tk.Frame(parent, bg="#182631", width=245, padx=18, pady=20)
        contacts.pack(side="left", fill="y", padx=(0, 18))
        contacts.pack_propagate(False)
        contact_header = tk.Frame(contacts, bg="#182631")
        contact_header.pack(fill="x")
        self._label(contact_header, "CONTACTS", 9, "#7f9aa5").pack(side="left")
        ttk.Button(contact_header, text="Refresh", command=self.refresh_contacts).pack(side="right")
        try:
            contact_names = self._do_fetch_contacts()
        except Exception as error:
            contact_names = []
            messagebox.showerror("Contacts unavailable", str(error))
        if not contact_names or self.current_contact not in contact_names:
            self.current_contact = None

        for index, name in enumerate(contact_names):
            status = "Available contact"
            button = tk.Button(contacts, text=f"  {name}\n  {status}", anchor="w", justify="left", bg="#243642" if name == self.current_contact else "#182631", fg="#f4f7f8", activebackground="#2b4552", activeforeground="#ffffff", relief="flat", bd=0, padx=8, pady=12, font=("Segoe UI", 10))
            button.pack(fill="x", pady=(18 if index == 0 else 6, 0))
            button.configure(command=lambda contact=name: self.select_contact(contact))
        self._label(contacts, "\nYour identity key\nRSA fingerprint verified", 9, "#6d8792", justify="left").pack(anchor="w", side="bottom")

    def show_admin(self):
        self._clear()
        header = tk.Frame(self.root, bg="#182631", height=72)
        header.pack(fill="x")
        header.pack_propagate(False)
        self._label(header, "ADMINISTRATIVE DASHBOARD", 11, "#2dd4bf").pack(side="left", padx=28)
        ttk.Button(header, text="Back to chat", command=lambda: self._transition(self.show_chat)).pack(side="right", padx=22, pady=16)

        content = tk.Frame(self.root, bg="#101820", padx=42, pady=34)
        content.pack(fill="both", expand=True)
        self.transition_target = content
        self._label(content, "Service status", 22, "#f4f7f8").pack(anchor="w")
        self._label(content, "Operational monitoring without message or contact visibility", 10, "#a9bbc3").pack(anchor="w", pady=(5, 26))
        status = tk.Frame(content, bg="#182631", padx=22, pady=18)
        status.pack(fill="x")
        self._label(status, "RELAY SERVICE", 9, "#7f9aa5").grid(row=0, column=0, sticky="w")
        self._label(status, "Healthy", 13, "#2dd4bf").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self._label(status, "REGISTERED USERS", 9, "#7f9aa5").grid(row=0, column=1, sticky="w", padx=100)
        self._label(status, "12", 13, "#f4f7f8").grid(row=1, column=1, sticky="w", padx=100, pady=(8, 0))

        users = tk.Frame(content, bg="#182631", padx=22, pady=18)
        users.pack(fill="x", pady=(20, 0))
        self._label(users, "ACCOUNT STATUS", 9, "#7f9aa5").grid(row=0, column=0, sticky="w")
        self._label(users, "Alice     Active", 11, "#f4f7f8").grid(row=1, column=0, sticky="w", pady=(18, 0))
        self._label(users, "Bob       Active", 11, "#f4f7f8").grid(row=2, column=0, sticky="w", pady=(10, 0))
        self._label(users, "Carol     Active", 11, "#f4f7f8").grid(row=3, column=0, sticky="w", pady=(10, 0))
        self._label(users, "SECURITY EVENTS", 9, "#7f9aa5").grid(row=0, column=1, sticky="w", padx=100)
        self._label(users, "No unresolved events", 11, "#2dd4bf").grid(row=1, column=1, sticky="w", padx=100, pady=(18, 0))

    def _build_conversation(self, parent):
        conversation = tk.Frame(parent, bg="#182631", padx=24, pady=20)
        conversation.pack(side="left", fill="both", expand=True)
        top = tk.Frame(conversation, bg="#182631")
        top.pack(fill="x")
        self.contact_title = self._label(top, self.current_contact or "", 19, "#f4f7f8")
        self.contact_title.pack(side="left")
        if self.current_contact:
            self._label(top, "  |  verified", 10, "#2dd4bf").pack(side="left", pady=(7, 0))
        self.transcript = tk.Text(conversation, bg="#101820", fg="#dce7ea", relief="flat", wrap="word", font=("Segoe UI", 11), padx=18, pady=16, state="disabled")
        self.transcript.pack(fill="both", expand=True, pady=(18, 14))
        self.composer = tk.Entry(conversation, bg="#101820", fg="#f4f7f8", insertbackground="#2dd4bf", relief="flat", font=("Segoe UI", 11))
        self.composer.pack(side="left", fill="x", expand=True, ipady=11)
        self.composer.bind("<Return>", lambda _event: self.send_message())
        ttk.Button(conversation, text="Send", style="Accent.TButton", command=self.send_message, state="normal" if self.current_contact else "disabled").pack(side="left", padx=(10, 0))
        self._render_messages()

    def select_contact(self, contact):
        self.current_contact = contact
        self._transition(self.show_chat)

    def refresh_contacts(self):
        self._transition(self.show_chat)

    def _render_messages(self):
        self.transcript.configure(state="normal")
        self.transcript.delete("1.0", "end")
        for sender, message in self.messages.get(self.current_contact, []):
            self.transcript.insert("end", f"{sender}\n", "sender")
            self.transcript.insert("end", f"{message}\n\n")
        self.transcript.tag_configure("sender", foreground="#2dd4bf", font=("Segoe UI", 9, "bold"))
        self.transcript.configure(state="disabled")

    def send_message(self):
        message = self.composer.get().strip()
        if not message or not self.current_contact:
            return
        if self.current_contact not in self.session_contacts:
            try:
                initiated = self._do_initiate_session(self.current_contact)
            except Exception as error:
                messagebox.showerror("Session unavailable", str(error))
                return
            if not initiated:
                messagebox.showerror("Session unavailable", f"Could not start a session with {self.current_contact}.")
                return
            self.session_contacts.add(self.current_contact)
        self.messages.setdefault(self.current_contact, []).append(("You", message))
        self.composer.delete(0, "end")
        error_message = "The message was not sent."
        try:
            sent = self._do_send_message(message, self.current_contact)
        except Exception as error:
            sent = False
            error_message = str(error)
        if not sent:
            self.messages[self.current_contact].pop()
            messagebox.showerror("Message failed", error_message)
        self._render_messages()

    # ===================================================
    # Logic functions
    # ===================================================

    def _connect_client(self, router_address):
        address = router_address.strip() or ROUTER_PLACEHOLDER
        if self.client is not None:
            self.client.stop()
        self.client = BaseClient(address).start()
        self.current_contact = None
        self.session_contacts = set()
        self.received_payload_index = 0
        self.messages = {}

    def _handle_login(self, username, password, router_address):
        username = username.strip()
        if not username or not password:
            messagebox.showerror("Login failed", "Username and password are required.")
            return
        self._connect_client(router_address)
        self.username = username
        try:
            if not self._do_login(self.username, password):
                messagebox.showerror("Login failed", "Invalid username or password.")
                return
            code = simpledialog.askstring("Two-factor verification", "Enter your verification code:")
            if not code or not self._do_2fa(code):
                messagebox.showerror("Verification failed", "The verification code was not accepted.")
                return
        except Exception as error:
            messagebox.showerror("Login failed", str(error))
            return
        self._transition(self.show_chat)

    def _prompt_registration(self, username, password, router_address):
        email = simpledialog.askstring("Create account", "Email address:")
        if email is not None:
            self._handle_register(username, password, email, router_address)

    def _handle_register(self, username, password, email, router_address):
        username = username.strip()
        email = email.strip()
        if not username or not password or not email:
            messagebox.showerror("Registration failed", "Username, password, and email are required.")
            return
        self._connect_client(router_address)
        self.username = username
        try:
            registered = self._do_register(self.username, password, email)
        except Exception as error:
            messagebox.showerror("Registration failed", str(error))
            return
        if registered:
            messagebox.showinfo("Account created", "Your account was created. You can now sign in.")
            self._transition(self.show_login)
        else:
            messagebox.showerror("Registration failed", "The account could not be created.")

    def _poll_received_messages(self):
        if self.client is not None:
            payloads = self.client.received_payloads
            while self.received_payload_index < len(payloads):
                message = self._on_receive_message(payloads[self.received_payload_index])
                self.received_payload_index += 1
                if message is not None:
                    sender, text = message
                    self.messages.setdefault(sender, []).append((sender, text))
                    if sender == self.current_contact and hasattr(self, "transcript"):
                        self._render_messages()
        self.root.after(250, self._poll_received_messages)

    # The following two methods are where the cryptographic operations would be performed
    def _create_payload(self, obj):
        data = json.dumps(obj)
        return Payload(data, SERVER_ADDR)

    def _decode_payload(self, payload):
        obj = json.loads(payload.data)
        return obj

    def _do_register(self, username, password, email):
        """
        Sending a registration request to the server with the provided username and password.
        """
        payload = self._create_payload({
            "type": "register", "username": username, "password": password, "email": email
        })
        resp = self.client._forward(self.client.router_addr, payload)
        resp_obj = self._decode_payload(resp)
        status_code = resp_obj.get("status_code")
        return status_code == 200

    def _do_login(self, username, password):
        """
        Sending a login request to the server with the provided username and password.
        """
        payload = self._create_payload({
            "type": "login",
            "username": username,
            "password": password,
            "router": self.client.router_addr,
            "client": self.client.address,
        })
        resp = self.client._forward(self.client.router_addr, payload)
        resp_obj = self._decode_payload(resp)
        status_code = resp_obj.get("status_code")
        return status_code == 200

    def _do_2fa(self, code):
        """
        Server will send a 2FA code to user email
        For purpose of debug a code 666 will always be accepted. (verification on serverside)
        """
        payload = self._create_payload({"type": "2fa", "code": code, "username": self.username})
        resp = self.client._forward(self.client.router_addr, payload)
        resp_obj = self._decode_payload(resp)
        status_code = resp_obj.get("status_code")
        return status_code == 200

    def _do_initiate_session(self, contact):
        """
        Initiate a secure session with a contact. This would involve key exchange and session establishment.
        """
        payload = self._create_payload({"type": "initiate_session", "contact": contact, "username": self.username})
        resp = self.client._forward(self.client.router_addr, payload)
        resp_obj = self._decode_payload(resp)
        status_code = resp_obj.get("status_code")
        # Should have more info about the session in the response
        return status_code == 200

    def _do_send_message(self, message, contact):
        """
        Send a message to a contact (The selected contact is the current contact in the UI)
        and wait for a response from the server. The server will forward the message to the contact's client.
        """
        payload = self._create_payload({"type": "message", "message": message, "target": contact, "username": self.username})
        resp = self.client._forward(self.client.router_addr, payload)
        resp_obj = self._decode_payload(resp)
        status_code = resp_obj.get("status_code")
        return status_code == 200

    def _do_fetch_contacts(self):
        """
        Send a request to the server to fetch the list of current active contacts for the current user.
        (Server will return contacts that last appeared within 1h of the request)
        """
        payload = self._create_payload({"type": "fetch_contacts", "username": self.username})
        resp = self.client._forward(self.client.router_addr, payload)
        resp_obj = self._decode_payload(resp)
        contacts = resp_obj.get("contacts", [])
        return contacts

    def _on_receive_message(self, payload):
        """
        Handle an incoming message payload from the server. 
        The payload is expected to contain the sender and the message.
        """
        obj = self._decode_payload(payload)
        sender = obj.get("sender")
        message = obj.get("message")
        if sender and message:
            return (sender, message)
        else:
            return None

    def close(self):
        if self.client is not None:
            self.client.stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    MessengerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
