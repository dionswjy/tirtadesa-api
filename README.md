# TirtaDesa Admin Web Only

Ini adalah tampilan admin web terpisah untuk backend FastAPI TirtaDesa.

## Cara Pakai

1. Pastikan FastAPI backend sudah berjalan:

```bash
python -m uvicorn main:app --reload
```

Biasanya backend jalan di:

```text
http://127.0.0.1:8000
```

2. Buka folder `tirtadesa_admin_web_only`.

3. Jalankan web frontend:

```bash
python -m http.server 5500
```

4. Buka browser:

```text
http://127.0.0.1:5500
```

## Ubah URL API

Kalau FastAPI kamu bukan di `http://127.0.0.1:8000`, buka file:

```text
assets/js/config.js
```

Ubah bagian:

```js
const API_BASE_URL = "http://127.0.0.1:8000";
```

## Endpoint yang Dipakai

Frontend ini memakai endpoint:

```text
POST /auth/login
GET  /auth/me
GET  /admin/dashboard

GET/POST/DELETE /admin/pelanggan
GET/POST/DELETE /admin/meter
GET/POST/DELETE /admin/catat-meter
GET/POST/DELETE /admin/tagihan
GET/POST/DELETE /admin/komplain
GET/POST/DELETE /admin/pemasangan-baru
```

## Login Default

Sesuai backend sebelumnya:

```text
Email    : admin@tirtadesa.com
Password : admin123
```
