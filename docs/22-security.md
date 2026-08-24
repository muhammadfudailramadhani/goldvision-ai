# Security

> Status dokumen: FASE 1 foundation — konten inti terverifikasi; detail diperkaya di fase berikutnya.

- Zero hardcoded secret — semua via env (§29)
- .gitignore: .env, generated/, db, venv
- Admin via ID allowlist, bukan username
- Validasi input: pair/TF whitelist di provider
