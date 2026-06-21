
const TOKEN_KEY = "tirtadesa_admin_token";
const USER_KEY = "tirtadesa_admin_user";

function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

function getUser() {
    try {
        return JSON.parse(localStorage.getItem(USER_KEY) || "{}");
    } catch {
        return {};
    }
}

function setAuth(data) {
    localStorage.setItem(TOKEN_KEY, data.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify({
        name: data.name,
        email: data.email,
        role: data.role
    }));
}

function logout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    showLogin();
}

async function apiFetch(path, options = {}) {
    const token = getToken();

    const headers = {
        "Content-Type": "application/json",
        ...(options.headers || {})
    };

    if (token) {
        headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE_URL}${path}`, {
        ...options,
        headers
    });

    const data = await response.json().catch(() => ({}));

    if (response.status === 401 || response.status === 403) {
        logout();
        throw new Error(data.detail || "Sesi habis. Silakan login ulang.");
    }

    if (!response.ok) {
        throw new Error(data.detail || "Terjadi kesalahan");
    }

    return data;
}

function showLogin() {
    document.getElementById("loginPage").classList.remove("hidden");
    document.getElementById("adminPage").classList.add("hidden");
}

function showAdmin() {
    document.getElementById("loginPage").classList.add("hidden");
    document.getElementById("adminPage").classList.remove("hidden");

    const user = getUser();
    document.getElementById("adminInfo").textContent = user.email
        ? `${user.name} (${user.email})`
        : "Admin";
}

async function handleLogin(event) {
    event.preventDefault();

    const message = document.getElementById("loginMessage");
    message.textContent = "";

    const email = document.getElementById("loginEmail").value.trim();
    const password = document.getElementById("loginPassword").value;

    try {
        const data = await apiFetch("/login", {
            method: "POST",
            body: JSON.stringify({ email, password })
        });

        setAuth(data);
        showAdmin();
        await openPage("dashboard");
    } catch (error) {
        message.textContent = error.message;
    }
}

function setActiveMenu(page) {
    document.querySelectorAll(".nav button").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.page === page);
    });
}

async function openPage(page) {
    showAdmin();
    setActiveMenu(page);

    const titleMap = {
        dashboard: "Dashboard",
        pelanggan: "Data Pelanggan",
        meter: "Data Meter Air",
        catatMeter: "Catat Meter",
        tagihan: "Data Tagihan",
        komplain: "Data Komplain",
        pemasanganBaru: "Pemasangan Baru"
    };

    document.getElementById("pageTitle").textContent = titleMap[page] || "Dashboard";

    if (page === "dashboard") return loadDashboard();
    if (page === "pelanggan") return loadPelanggan();
    if (page === "meter") return loadMeter();
    if (page === "catatMeter") return loadCatatMeter();
    if (page === "tagihan") return loadTagihan();
    if (page === "komplain") return loadKomplain();
    if (page === "pemasanganBaru") return loadPemasanganBaru();
}

function rupiah(value) {
    const number = Number(value || 0);
    return new Intl.NumberFormat("id-ID", {
        style: "currency",
        currency: "IDR",
        maximumFractionDigits: 0
    }).format(number);
}

function safe(value) {
    return value === null || value === undefined || value === "" ? "-" : value;
}

function badge(value) {
    const v = String(value || "-");
    let cls = "";

    if (["aktif", "lunas", "selesai", "diterima", "verified"].includes(v)) cls = "success";
    if (["pending", "baru", "diajukan", "belum_lunas", "diproses"].includes(v)) cls = "warning";
    if (["blacklist", "ditolak", "rejected", "nonaktif"].includes(v)) cls = "danger";

    return `<span class="badge ${cls}">${safe(v)}</span>`;
}

function render(html) {
    document.getElementById("pageContent").innerHTML = html;
}

async function submitData(event, endpoint, reloadFnName) {
    event.preventDefault();

    const form = event.target;
    const payload = {};

    new FormData(form).forEach((value, key) => {
        if (value === "") return;

        if (["pelanggan_id", "meter_id"].includes(key)) {
            payload[key] = Number(value);
        } else if ([
            "angka_meter_lalu",
            "angka_meter_kini",
            "penggunaan_m3",
            "total_tagihan"
        ].includes(key)) {
            payload[key] = Number(value);
        } else {
            payload[key] = value;
        }
    });

    try {
        await apiFetch(endpoint, {
            method: "POST",
            body: JSON.stringify(payload)
        });

        form.reset();
        await window[reloadFnName]();
        alert("Data berhasil disimpan");
    } catch (error) {
        alert(error.message);
    }
}

async function deleteData(endpoint, reloadFnName) {
    if (!confirm("Yakin ingin menghapus data ini?")) return;

    try {
        await apiFetch(endpoint, { method: "DELETE" });
        await window[reloadFnName]();
    } catch (error) {
        alert(error.message);
    }
}

async function loadDashboard() {
    try {
        const data = await apiFetch("/admin/dashboard");

        render(`
            <div class="cards">
                <div class="card">
                    <div class="card-title">Total Pelanggan</div>
                    <div class="card-value">${data.total_pelanggan ?? 0}</div>
                </div>
                <div class="card">
                    <div class="card-title">Total Meter</div>
                    <div class="card-value">${data.total_meter ?? 0}</div>
                </div>
                <div class="card">
                    <div class="card-title">Komplain Baru</div>
                    <div class="card-value">${data.komplain_baru ?? 0}</div>
                </div>
                <div class="card">
                    <div class="card-title">Pengajuan Baru</div>
                    <div class="card-value">${data.pengajuan_pemasangan_baru ?? 0}</div>
                </div>
                <div class="card">
                    <div class="card-title">Tagihan Belum Lunas</div>
                    <div class="card-value">${data.tagihan_belum_lunas ?? 0}</div>
                </div>
            </div>

            <div class="panel">
                <h2>Selamat datang di Admin TirtaDesa</h2>
                <p class="notice">
                    Ini adalah tampilan admin web terpisah. Data diambil langsung dari backend FastAPI kamu.
                </p>
            </div>
        `);
    } catch (error) {
        render(`<div class="panel"><p class="message">${error.message}</p></div>`);
    }
}

async function loadPelanggan() {
    const data = await apiFetch("/pelanggan");

    render(`
        <div class="panel">
            <div class="panel-header">
                <h2>Tambah Pelanggan</h2>
            </div>

            <form class="grid-form" onsubmit="submitData(event, '/pelanggan', 'loadPelanggan')">
                <div class="form-group">
                    <label>Nama</label>
                    <input name="nama" required>
                </div>
                <div class="form-group">
                    <label>NIK</label>
                    <input name="nik">
                </div>
                <div class="form-group">
                    <label>No HP</label>
                    <input name="no_hp">
                </div>
                <div class="form-group span-2">
                    <label>Alamat</label>
                    <input name="alamat" required>
                </div>
                <div class="form-group">
                    <label>Status Pelanggan</label>
                    <select name="status_pelanggan">
                        <option value="aktif">Aktif</option>
                        <option value="blacklist">Blacklist</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Jenis Pelanggan</label>
                    <select name="jenis_pelanggan">
                        <option value="non_subsidi">Non Subsidi</option>
                        <option value="subsidi">Subsidi</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>&nbsp;</label>
                    <button class="btn btn-primary" type="submit">Simpan</button>
                </div>
            </form>
        </div>

        <div class="panel">
            <div class="panel-header">
                <h2>Daftar Pelanggan</h2>
            </div>

            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Nama</th>
                            <th>NIK</th>
                            <th>Alamat</th>
                            <th>No HP</th>
                            <th>Status</th>
                            <th>Jenis</th>
                            <th>Aksi</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.length ? data.map(item => `
                            <tr>
                                <td>${item.id}</td>
                                <td>${safe(item.nama)}</td>
                                <td>${safe(item.nik)}</td>
                                <td>${safe(item.alamat)}</td>
                                <td>${safe(item.no_hp)}</td>
                                <td>${badge(item.status_pelanggan)}</td>
                                <td>${badge(item.jenis_pelanggan)}</td>
                                <td>
                                    <button class="btn btn-danger" onclick="deleteData('/pelanggan/${item.id}', 'loadPelanggan')">Hapus</button>
                                </td>
                            </tr>
                        `).join("") : `<tr><td colspan="8" class="empty">Belum ada data pelanggan</td></tr>`}
                    </tbody>
                </table>
            </div>
        </div>
    `);
}

async function loadMeter() {
    const data = await apiFetch("/meter");

    render(`
        <div class="panel">
            <div class="panel-header">
                <h2>Tambah Meter Air</h2>
            </div>

            <form class="grid-form" onsubmit="submitData(event, '/meter', 'loadMeter')">
                <div class="form-group">
                    <label>ID Pelanggan</label>
                    <input name="pelanggan_id" type="number" required>
                </div>
                <div class="form-group">
                    <label>No Meter</label>
                    <input name="no_meter" required>
                </div>
                <div class="form-group">
                    <label>Status Meter</label>
                    <select name="status_meter">
                        <option value="aktif">Aktif</option>
                        <option value="nonaktif">Nonaktif</option>
                    </select>
                </div>
                <div class="form-group span-2">
                    <label>Alamat Lokasi</label>
                    <input name="alamat_lokasi">
                </div>
                <div class="form-group">
                    <label>&nbsp;</label>
                    <button class="btn btn-primary" type="submit">Simpan</button>
                </div>
            </form>
        </div>

        <div class="panel">
            <div class="panel-header">
                <h2>Daftar Meter Air</h2>
            </div>

            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>ID Pelanggan</th>
                            <th>No Meter</th>
                            <th>Lokasi</th>
                            <th>Status</th>
                            <th>Aksi</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.length ? data.map(item => `
                            <tr>
                                <td>${item.id}</td>
                                <td>${item.pelanggan_id}</td>
                                <td>${safe(item.no_meter)}</td>
                                <td>${safe(item.alamat_lokasi)}</td>
                                <td>${badge(item.status_meter)}</td>
                                <td>
                                    <button class="btn btn-danger" onclick="deleteData('/meter/${item.id}', 'loadMeter')">Hapus</button>
                                </td>
                            </tr>
                        `).join("") : `<tr><td colspan="6" class="empty">Belum ada data meter</td></tr>`}
                    </tbody>
                </table>
            </div>
        </div>
    `);
}

async function loadCatatMeter() {
    const data = await apiFetch("/catat-meter");

    render(`
        <div class="panel">
            <div class="panel-header">
                <h2>Tambah Catatan Meter</h2>
            </div>

            <form class="grid-form" onsubmit="submitData(event, '/admin/catat-meter', 'loadCatatMeter')">
                <div class="form-group">
                    <label>ID Meter</label>
                    <input name="meter_id" type="number" required>
                </div>
                <div class="form-group">
                    <label>Bulan</label>
                    <input name="bulan" placeholder="2026-06" required>
                </div>
                <div class="form-group">
                    <label>Nama Petugas</label>
                    <input name="petugas_nama">
                </div>
                <div class="form-group">
                    <label>Angka Meter Lalu</label>
                    <input name="angka_meter_lalu" type="number" step="0.01" required>
                </div>
                <div class="form-group">
                    <label>Angka Meter Kini</label>
                    <input name="angka_meter_kini" type="number" step="0.01" required>
                </div>
                <div class="form-group">
                    <label>&nbsp;</label>
                    <button class="btn btn-primary" type="submit">Simpan</button>
                </div>
            </form>
        </div>

        <div class="panel">
            <div class="panel-header">
                <h2>Daftar Catat Meter</h2>
            </div>

            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>ID Meter</th>
                            <th>Bulan</th>
                            <th>Meter Lalu</th>
                            <th>Meter Kini</th>
                            <th>Penggunaan</th>
                            <th>Petugas</th>
                            <th>Status</th>
                            <th>Aksi</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.length ? data.map(item => `
                            <tr>
                                <td>${item.id}</td>
                                <td>${item.meter_id}</td>
                                <td>${safe(item.bulan)}</td>
                                <td>${item.angka_meter_lalu}</td>
                                <td>${item.angka_meter_kini}</td>
                                <td>${item.penggunaan_m3} m³</td>
                                <td>${safe(item.petugas_nama)}</td>
                                <td>${badge(item.status_verifikasi)}</td>
                                <td>
                                    <button class="btn btn-danger" onclick="deleteData('/admin/catat-meter/${item.id}', 'loadCatatMeter')">Hapus</button>
                                </td>
                            </tr>
                        `).join("") : `<tr><td colspan="9" class="empty">Belum ada data catat meter</td></tr>`}
                    </tbody>
                </table>
            </div>
        </div>
    `);
}

async function loadTagihan() {
    const data = await apiFetch("/admin/tagihan");

    render(`
        <div class="panel">
            <div class="panel-header">
                <h2>Tambah Tagihan</h2>
            </div>

            <form class="grid-form" onsubmit="submitData(event, '/admin/tagihan', 'loadTagihan')">
                <div class="form-group">
                    <label>ID Meter</label>
                    <input name="meter_id" type="number" required>
                </div>
                <div class="form-group">
                    <label>Bulan</label>
                    <input name="bulan" placeholder="2026-06" required>
                </div>
                <div class="form-group">
                    <label>Penggunaan m³</label>
                    <input name="penggunaan_m3" type="number" step="0.01" required>
                </div>
                <div class="form-group">
                    <label>Total Tagihan</label>
                    <input name="total_tagihan" type="number" required>
                </div>
                <div class="form-group">
                    <label>Status Pembayaran</label>
                    <select name="status_pembayaran">
                        <option value="belum_lunas">Belum Lunas</option>
                        <option value="lunas">Lunas</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>&nbsp;</label>
                    <button class="btn btn-primary" type="submit">Simpan</button>
                </div>
            </form>
        </div>

        <div class="panel">
            <div class="panel-header">
                <h2>Daftar Tagihan</h2>
            </div>

            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>ID Meter</th>
                            <th>Bulan</th>
                            <th>Penggunaan</th>
                            <th>Total</th>
                            <th>Status</th>
                            <th>Tanggal Bayar</th>
                            <th>Aksi</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.length ? data.map(item => `
                            <tr>
                                <td>${item.id}</td>
                                <td>${item.meter_id}</td>
                                <td>${safe(item.bulan)}</td>
                                <td>${item.penggunaan_m3} m³</td>
                                <td>${rupiah(item.total_tagihan)}</td>
                                <td>${badge(item.status_pembayaran)}</td>
                                <td>${safe(item.tanggal_bayar)}</td>
                                <td>
                                    <button class="btn btn-danger" onclick="deleteData('/admin/tagihan/${item.id}', 'loadTagihan')">Hapus</button>
                                </td>
                            </tr>
                        `).join("") : `<tr><td colspan="8" class="empty">Belum ada data tagihan</td></tr>`}
                    </tbody>
                </table>
            </div>
        </div>
    `);
}

async function loadKomplain() {
    const data = await apiFetch("/admin/komplain");

    render(`
        <div class="panel">
            <div class="panel-header">
                <h2>Tambah Komplain</h2>
            </div>

            <form class="grid-form" onsubmit="submitData(event, '/admin/komplain', 'loadKomplain')">
                <div class="form-group">
                    <label>ID Pelanggan</label>
                    <input name="pelanggan_id" type="number" required>
                </div>
                <div class="form-group span-2">
                    <label>Judul</label>
                    <input name="judul" required>
                </div>
                <div class="form-group span-3">
                    <label>Deskripsi</label>
                    <textarea name="deskripsi" required></textarea>
                </div>
                <div class="form-group">
                    <button class="btn btn-primary" type="submit">Simpan</button>
                </div>
            </form>
        </div>

        <div class="panel">
            <div class="panel-header">
                <h2>Daftar Komplain</h2>
            </div>

            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>ID Pelanggan</th>
                            <th>Judul</th>
                            <th>Deskripsi</th>
                            <th>Status</th>
                            <th>Dibuat</th>
                            <th>Aksi</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.length ? data.map(item => `
                            <tr>
                                <td>${item.id}</td>
                                <td>${item.pelanggan_id}</td>
                                <td>${safe(item.judul)}</td>
                                <td>${safe(item.deskripsi)}</td>
                                <td>${badge(item.status)}</td>
                                <td>${safe(item.created_at)}</td>
                                <td>
                                    <button class="btn btn-danger" onclick="deleteData('/admin/komplain/${item.id}', 'loadKomplain')">Hapus</button>
                                </td>
                            </tr>
                        `).join("") : `<tr><td colspan="7" class="empty">Belum ada data komplain</td></tr>`}
                    </tbody>
                </table>
            </div>
        </div>
    `);
}

async function loadPemasanganBaru() {
    const data = await apiFetch("/admin/pemasangan-baru");

    render(`
        <div class="panel">
            <div class="panel-header">
                <h2>Tambah Pengajuan Pemasangan</h2>
            </div>

            <form class="grid-form" onsubmit="submitData(event, '/admin/pemasangan-baru', 'loadPemasanganBaru')">
                <div class="form-group">
                    <label>Nama</label>
                    <input name="nama" required>
                </div>
                <div class="form-group">
                    <label>NIK</label>
                    <input name="nik">
                </div>
                <div class="form-group">
                    <label>No HP</label>
                    <input name="no_hp">
                </div>
                <div class="form-group span-2">
                    <label>Alamat</label>
                    <input name="alamat" required>
                </div>
                <div class="form-group">
                    <label>Jenis Pelanggan</label>
                    <select name="jenis_pelanggan">
                        <option value="non_subsidi">Non Subsidi</option>
                        <option value="subsidi">Subsidi</option>
                    </select>
                </div>
                <div class="form-group">
                    <button class="btn btn-primary" type="submit">Simpan</button>
                </div>
            </form>
        </div>

        <div class="panel">
            <div class="panel-header">
                <h2>Daftar Pengajuan</h2>
            </div>

            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Nama</th>
                            <th>NIK</th>
                            <th>Alamat</th>
                            <th>No HP</th>
                            <th>Jenis</th>
                            <th>Status</th>
                            <th>Aksi</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.length ? data.map(item => `
                            <tr>
                                <td>${item.id}</td>
                                <td>${safe(item.nama)}</td>
                                <td>${safe(item.nik)}</td>
                                <td>${safe(item.alamat)}</td>
                                <td>${safe(item.no_hp)}</td>
                                <td>${badge(item.jenis_pelanggan)}</td>
                                <td>${badge(item.status)}</td>
                                <td>
                                    <button class="btn btn-danger" onclick="deleteData('/admin/pemasangan-baru/${item.id}', 'loadPemasanganBaru')">Hapus</button>
                                </td>
                            </tr>
                        `).join("") : `<tr><td colspan="8" class="empty">Belum ada pengajuan pemasangan</td></tr>`}
                    </tbody>
                </table>
            </div>
        </div>
    `);
}

function initApp() {
    document.getElementById("loginForm").addEventListener("submit", handleLogin);

    document.querySelectorAll(".nav button[data-page]").forEach(btn => {
        btn.addEventListener("click", () => openPage(btn.dataset.page));
    });

    if (getToken()) {
        showAdmin();
        openPage("dashboard");
    } else {
        showLogin();
    }
}

window.addEventListener("DOMContentLoaded", initApp);
