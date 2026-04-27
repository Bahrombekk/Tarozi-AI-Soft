import base64
import json
import os
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad


def universal_decode(data: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp1251", "latin1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue

    return data.decode("utf-8", errors="replace")


class Cipher:

    def __init__(self):
        self.current_path: str = os.getcwd()
        self.salt: bytes = base64.b64decode(
            os.environ.get(
                "TAROZI_CIPHER_SALT",
                base64.b64encode(
                    b"L\xc9^\x12\x9d@g\xcdsH\xb3\x88\xf3\xf7!\x1c}\x1b\x14Y\x81\xfe\x97\\5\x95\xb3\x1fGl\xf7\xd3"
                ).decode()
            )
        )
        self.msg: str = os.environ.get("TAROZI_CIPHER_PASSWORD", "LZVnqSHDaJA3KK9JcjC8")

        self.settings_path = os.path.join(self.current_path, "settings")
        if not os.path.exists(self.settings_path):
            os.mkdir(self.settings_path)

        self.key_file = os.path.join(self.settings_path, "key.bin")
        if not os.path.exists(self.key_file):
            key_bytes = PBKDF2(password=self.msg, salt=self.salt, dkLen=32)
            with open(self.key_file, "wb") as key_f:
                key_f.write(key_bytes)

        with open(self.key_file, "rb") as key_f:
            self.key = key_f.read()

    def get_bin_data(self, file_path: str) -> list[str]:
        try:
            if not os.path.exists(file_path):
                return []

            with open(file_path, "rb") as f:
                iv = f.read(16)
                encrypted = f.read()

            if not encrypted:
                return []

            ciph = AES.new(self.key, AES.MODE_CBC, iv=iv)
            decrypted_bytes = unpad(ciph.decrypt(encrypted), AES.block_size)
            decrypted_text = decrypted_bytes.decode("utf-8")
            return decrypted_text.split("\n")

        except Exception:
            return []

    def add_bin_data(self, file_path: str, data: str | None = None) -> None:
        if data is None:
            return
        try:
            old_lines: list[str] = []
            if os.path.exists(file_path):
                old_lines = self.get_bin_data(file_path)

            all_lines = old_lines + [data]
            text_to_encrypt = "\n".join(all_lines).strip()

            ciph = AES.new(self.key, AES.MODE_CBC)
            encrypted_data = ciph.encrypt(pad(text_to_encrypt.encode("utf-8"), AES.block_size))

            with open(file_path, "wb") as f:
                f.write(ciph.iv)
                f.write(encrypted_data)

        except (ValueError, Exception) as err:
            print(f"[bin_files.Cipher.add_bin_data] ERROR: {err}")

    def read_bin_file(self, file_path: str) -> list[str]:
        return self.get_bin_data(file_path)

    def write(self, file_path: str, data: list[str] | dict = None) -> None:
        try:
            if data is None:
                return
            if isinstance(data, list):
                text_to_encrypt = "\n".join(data).strip()
            elif isinstance(data, dict):
                text_to_encrypt = json.dumps(data)
            else:
                return

            ciph = AES.new(self.key, AES.MODE_CBC)
            encrypted_data = ciph.encrypt(pad(text_to_encrypt.encode("utf-8"), AES.block_size))

            with open(file_path, "wb") as f:
                f.write(ciph.iv)
                f.write(encrypted_data)

        except Exception as err:
            print(f"[bin_files.Cipher.write] ERROR: {err}")

    def read(self, file_path: str) -> list[str] | dict:
        try:
            if not os.path.exists(file_path):
                return []

            with open(file_path, "rb") as f:
                iv = f.read(16)
                encrypted = f.read()

            if not encrypted:
                return []

            cr = AES.new(self.key, AES.MODE_CBC, iv=iv)
            decrypted_bytes = unpad(cr.decrypt(encrypted), AES.block_size)
            decrypted_text = decrypted_bytes.decode("utf-8").strip()

            try:
                return json.loads(decrypted_text)
            except json.JSONDecodeError:
                return decrypted_text.split("\n")

        except Exception as err:
            print(f"[bin_files.Cipher.read] ERROR: {err}")
            return []

    def encrypt_text(self, text: str) -> str:
        try:
            cr = AES.new(self.key, AES.MODE_CBC)
            encrypted = cr.encrypt(pad(text.encode("utf-8"), AES.block_size))
            data = cr.iv + encrypted
            return base64.b64encode(data).decode("utf-8")
        except Exception as err:
            print(f"[bin_files.Cipher.encrypt_text] ERROR: {err}")
            return ""

    def decrypt_text(self, encrypted_b64: str) -> str:
        try:
            encrypted_data = base64.b64decode(encrypted_b64.encode("utf-8"))
            iv = encrypted_data[:16]
            ciphertext = encrypted_data[16:]
            cr = AES.new(self.key, AES.MODE_CBC, iv=iv)
            decrypted = unpad(cr.decrypt(ciphertext), AES.block_size)
            return decrypted.decode("utf-8")
        except Exception as err:
            print(f"[bin_files.Cipher.decrypt_text] ERROR: {err}")
            return ""

    def encrypt_dict(self, data: dict) -> str:
        try:
            text = json.dumps(data)
            return self.encrypt_text(text)
        except Exception as err:
            print(f"[bin_files.Cipher.encrypt_dict] ERROR: {err}")
            return ""

    def decrypt_dict(self, encrypted_b64: str) -> dict:
        try:
            decrypted_text = self.decrypt_text(encrypted_b64)
            if decrypted_text:
                return json.loads(decrypted_text)
            return {}
        except Exception as err:
            print(f"[bin_files.Cipher.decrypt_dict] ERROR: {err}")
            return {}


# Module-level singleton instance
cipher: Cipher = Cipher()

