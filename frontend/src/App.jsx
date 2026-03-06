import { useEffect, useMemo, useState } from "react";

const API = import.meta.env.VITE_API_URL || "/api";
const authHeaders = (token) => (token ? { Authorization: `Bearer ${token}` } : {});

function Alert({ msg, onClose }) {
  if (!msg) return null;

  const bg =
    msg.type === "success"
      ? "#0f2f1a"
      : msg.type === "error"
      ? "#2f0f12"
      : "#1a1a1a";

  return (
    <div
      style={{
        padding: 12,
        borderRadius: 10,
        marginBottom: 14,
        border: "1px solid #333",
        background: bg,
      }}
    >
      <b style={{ textTransform: "capitalize" }}>{msg.type}:</b> {msg.text}
      <button onClick={onClose} style={{ float: "right" }}>
        x
      </button>
    </div>
  );
}

export default function App() {
  // ===== Auth =====
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [role, setRole] = useState(localStorage.getItem("role") || "");
  const [username, setUsername] = useState(localStorage.getItem("username") || "");
  const [msg, setMsg] = useState(null);

  // ===== UI =====
  const [tab, setTab] = useState("tracks"); // tracks | artists | genres | purchases

  // ===== Login/Register =====
  const [u, setU] = useState("admin");
  const [email, setEmail] = useState("admin@chinook.local");
  const [p, setP] = useState("Admin123!");

  // ===== Tracks =====
  const [trackQuery, setTrackQuery] = useState("Love");
  const [tracks, setTracks] = useState([]);
  const [loadingTracks, setLoadingTracks] = useState(false);

  // ===== Purchases (user) =====
  const [purchases, setPurchases] = useState([]);
  const [loadingPurchases, setLoadingPurchases] = useState(false);

  // ===== Artists stats =====
  const [artistQuery, setArtistQuery] = useState("");
  const [artistStats, setArtistStats] = useState([]);
  const [loadingArtists, setLoadingArtists] = useState(false);

  // ===== Genres stats =====
  const [genreQuery, setGenreQuery] = useState("");
  const [genreStats, setGenreStats] = useState([]);
  const [loadingGenres, setLoadingGenres] = useState(false);

  // ===== Admin: dropdown data =====
  const [adminArtists, setAdminArtists] = useState([]);
  const [adminGenres, setAdminGenres] = useState([]);
  const [adminAlbums, setAdminAlbums] = useState([]);

  // ===== Admin: create form =====
  const [createName, setCreateName] = useState("");
  const [createPrice, setCreatePrice] = useState("0.99");
  const [createArtistId, setCreateArtistId] = useState("");
  const [createGenreId, setCreateGenreId] = useState("");

  const [albumMode, setAlbumMode] = useState("existing"); // existing | new
  const [createAlbumId, setCreateAlbumId] = useState("");
  const [createAlbumTitle, setCreateAlbumTitle] = useState("");

  // ===== Admin: inline edit =====
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState("");
  const [editPrice, setEditPrice] = useState("");

  // ===== Helpers =====
  const purchasedIds = useMemo(
    () => new Set((purchases || []).map((x) => x.TrackId)),
    [purchases]
  );

  const artistLabel = (a) => a.ArtistName ?? a.Name ?? `Artist ${a.ArtistId}`;
  const genreLabel = (g) => g.GenreName ?? g.Name ?? `Genre ${g.GenreId}`;
  const albumLabel = (al) => al.Title ?? al.AlbumTitle ?? `Album ${al.AlbumId}`;

  // ===========================
  // AUTH
  // ===========================
  async function doRegister() {
    setMsg(null);
    try {
      const r = await fetch(`${API}/v1/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: u, email, password: p }),
      });

      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data?.detail || `HTTP ${r.status}`);

      setMsg({ type: "success", text: "Registro OK. Ahora haz login." });
    } catch (e) {
      setMsg({ type: "error", text: `Registro falló: ${e.message}` });
    }
  }

  async function doLogin() {
    setMsg(null);
    try {
      const body = new URLSearchParams();
      body.set("username", u);
      body.set("password", p);

      const r = await fetch(`${API}/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });

      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data?.detail || `HTTP ${r.status}`);

      localStorage.setItem("token", data.access_token);
      localStorage.setItem("role", data.role);
      localStorage.setItem("username", data.username);

      setToken(data.access_token);
      setRole(data.role);
      setUsername(data.username);
      setPurchases([]);

      setMsg({
        type: "success",
        text: `Login OK como ${data.username} (${data.role})`,
      });

      if (data.role === "admin") {
        setTab("tracks");
      }
    } catch (e) {
      setMsg({ type: "error", text: `Login falló: ${e.message}` });
    }
  }

  function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    localStorage.removeItem("username");
    setToken("");
    setRole("");
    setUsername("");
    setPurchases([]);
    setTab("tracks");
    setMsg({ type: "info", text: "Sesión cerrada." });
  }

  // ===========================
  // TRACKS
  // ===========================
  async function loadTracks() {
    setLoadingTracks(true);
    setMsg(null);
    try {
      const r = await fetch(`${API}/v1/tracks?query=${encodeURIComponent(trackQuery)}`);
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data?.detail || `HTTP ${r.status}`);
      setTracks(data.items || []);
      if ((data.items || []).length === 0) {
        setMsg({ type: "info", text: "Sin resultados." });
      }
    } catch (e) {
      setMsg({ type: "error", text: `Buscar tracks falló: ${e.message}` });
    } finally {
      setLoadingTracks(false);
    }
  }

  // ===========================
  // PURCHASES (user)
  // ===========================
  async function loadPurchases() {
    if (!token || role !== "user") return;

    setLoadingPurchases(true);
    try {
      const r = await fetch(`${API}/v1/purchases`, {
        headers: { ...authHeaders(token) },
      });

      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data?.detail || `HTTP ${r.status}`);

      setPurchases(data.items || []);
    } catch (e) {
      setMsg({ type: "error", text: `Cargar compras falló: ${e.message}` });
    } finally {
      setLoadingPurchases(false);
    }
  }

  async function buy(trackId) {
    if (purchasedIds.has(trackId)) {
      setMsg({ type: "info", text: "Ya compraste esta canción." });
      return;
    }

    setMsg(null);
    try {
      const r = await fetch(`${API}/v1/purchases`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...authHeaders(token),
        },
        body: JSON.stringify({
          track_id: trackId,
          quantity: 1,
        }),
      });

      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data?.detail || `HTTP ${r.status}`);

      setMsg({ type: "success", text: `Compra OK ✅ Total: ${data.total}` });
      await loadPurchases();
    } catch (e) {
      setMsg({ type: "error", text: `Compra falló: ${e.message}` });
    }
  }

  // ===========================
  // STATS: Artists / Genres
  // ===========================
  async function searchArtistsStats() {
    setLoadingArtists(true);
    setMsg(null);
    try {
      const r = await fetch(`${API}/v1/stats/artists?query=${encodeURIComponent(artistQuery)}`);
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data?.detail || `HTTP ${r.status}`);
      setArtistStats(data.items || []);
    } catch (e) {
      setMsg({ type: "error", text: `Buscar artistas falló: ${e.message}` });
    } finally {
      setLoadingArtists(false);
    }
  }

  async function searchGenresStats() {
    setLoadingGenres(true);
    setMsg(null);
    try {
      const r = await fetch(`${API}/v1/stats/genres?query=${encodeURIComponent(genreQuery)}`);
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data?.detail || `HTTP ${r.status}`);
      setGenreStats(data.items || []);
    } catch (e) {
      setMsg({ type: "error", text: `Buscar géneros falló: ${e.message}` });
    } finally {
      setLoadingGenres(false);
    }
  }

  // ===========================
  // ADMIN: load dropdown data
  // ===========================
  async function loadAdminArtists() {
    const r = await fetch(`${API}/v1/stats/artists?query=`);
    const data = await r.json().catch(() => ({}));
    setAdminArtists(data.items || []);
  }

  async function loadAdminGenres() {
    const r = await fetch(`${API}/v1/stats/genres?query=`);
    const data = await r.json().catch(() => ({}));
    setAdminGenres(data.items || []);
  }

  async function loadAlbumsForArtist(artistId) {
    if (!artistId) {
      setAdminAlbums([]);
      return;
    }

    const r = await fetch(
      `${API}/v1/albums?artist_id=${encodeURIComponent(artistId)}&query=`
    );
    const data = await r.json().catch(() => ({}));

    if (!r.ok) {
      setAdminAlbums([]);
      setMsg({
        type: "error",
        text: `Cargar álbumes falló: ${data?.detail || `HTTP ${r.status}`}`,
      });
      return;
    }

    setAdminAlbums(data.items || []);
  }

  // ===========================
  // ADMIN: CRUD
  // ===========================
  async function adminCreateTrack() {
    setMsg(null);

    try {
      if (!createName.trim() || !createArtistId || !createPrice) {
        throw new Error("Faltan: nombre, artista, precio");
      }

      const payload = {
        name: createName.trim(),
        unit_price: Number(createPrice),
        artist_id: Number(createArtistId),
        genre_id: createGenreId ? Number(createGenreId) : 0,
      };

      if (albumMode === "existing") {
        if (!createAlbumId) throw new Error("Selecciona un álbum");
        payload.album_id = Number(createAlbumId);
      } else {
        if (!createAlbumTitle.trim()) throw new Error("Escribe el nombre del nuevo álbum");
        payload.album_title = createAlbumTitle.trim();
      }

      const r = await fetch(`${API}/v1/admin/tracks`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...authHeaders(token),
        },
        body: JSON.stringify(payload),
      });

      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data?.detail || `HTTP ${r.status}`);

      setMsg({ type: "success", text: `Canción creada ✅ ID=${data.track_id}` });

      setCreateName("");
      setCreatePrice("0.99");
      setCreateGenreId("");
      setCreateAlbumId("");
      setCreateAlbumTitle("");
      setAdminAlbums([]);

      await loadTracks();
    } catch (e) {
      setMsg({ type: "error", text: `Crear falló: ${e.message}` });
    }
  }

  async function adminSaveEdit(trackId) {
    setMsg(null);

    try {
      const r = await fetch(`${API}/v1/admin/tracks/${trackId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          ...authHeaders(token),
        },
        body: JSON.stringify({
          name: editName,
          unit_price: Number(editPrice),
        }),
      });

      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data?.detail || `HTTP ${r.status}`);

      setMsg({ type: "success", text: "Canción actualizada ✅" });
      setEditingId(null);
      await loadTracks();
    } catch (e) {
      setMsg({ type: "error", text: `Editar falló: ${e.message}` });
    }
  }

  async function adminDeleteTrack(trackId) {
    setMsg(null);

    try {
      const ok = window.confirm(`¿Eliminar TrackId=${trackId}?`);
      if (!ok) return;

      const r = await fetch(`${API}/v1/admin/tracks/${trackId}`, {
        method: "DELETE",
        headers: { ...authHeaders(token) },
      });

      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data?.detail || `HTTP ${r.status}`);

      setMsg({ type: "success", text: "Canción eliminada ✅" });
      await loadTracks();
    } catch (e) {
      setMsg({ type: "error", text: `Eliminar falló: ${e.message}` });
    }
  }

  // ===========================
  // Effects
  // ===========================
  useEffect(() => {
    loadTracks();
  }, []);

  useEffect(() => {
    if (token && role === "user") {
      loadPurchases();
    }
  }, [token, role]);

  useEffect(() => {
    if (role === "admin" && tab === "purchases") {
      setTab("tracks");
    }
  }, [role, tab]);

  useEffect(() => {
    if (tab === "purchases" && token && role === "user") {
      loadPurchases();
    }
  }, [tab]);

  useEffect(() => {
    if (tab === "artists") searchArtistsStats();
    if (tab === "genres") searchGenresStats();
  }, [tab]);

  useEffect(() => {
    if (token && role === "admin") {
      loadAdminArtists().catch(() => {});
      loadAdminGenres().catch(() => {});
    }
  }, [token, role]);

  useEffect(() => {
    if (token && role === "admin" && createArtistId && albumMode === "existing") {
      loadAlbumsForArtist(createArtistId).catch(() => {});
    }
  }, [token, role, createArtistId, albumMode]);

  // ===========================
  // Render
  // ===========================
  return (
    <div
      style={{
        maxWidth: 1150,
        margin: "0 auto",
        padding: 20,
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <h1 style={{ marginBottom: 6 }}>Chinook Store</h1>
      <div style={{ opacity: 0.75, marginBottom: 12 }}>
        Admin CRUD · User compras · Stats Artistas/Géneros
      </div>

      <Alert msg={msg} onClose={() => setMsg(null)} />

      {!token ? (
        <div
          style={{
            border: "1px solid #333",
            borderRadius: 12,
            padding: 14,
            marginBottom: 16,
          }}
        >
          <h3>Login / Register</h3>
          <div style={{ display: "flex", gap: 10, marginBottom: 10 }}>
            <input
              value={u}
              onChange={(e) => setU(e.target.value)}
              placeholder="username"
              style={{ flex: 1, padding: 10 }}
            />
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="email"
              style={{ flex: 1, padding: 10 }}
            />
            <input
              value={p}
              onChange={(e) => setP(e.target.value)}
              placeholder="password"
              type="password"
              style={{ flex: 1, padding: 10 }}
            />
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <button onClick={doLogin} style={{ padding: "8px 12px" }}>
              Login
            </button>
            <button onClick={doRegister} style={{ padding: "8px 12px" }}>
              Register
            </button>
          </div>
        </div>
      ) : (
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 14 }}>
          <div>
            Sesión: <b>{username}</b> · Rol: <b>{role}</b>
          </div>
          <button onClick={logout}>Logout</button>
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: "flex", gap: 10, marginBottom: 14 }}>
        <button onClick={() => setTab("tracks")} disabled={tab === "tracks"}>
          Tracks
        </button>
        <button onClick={() => setTab("artists")} disabled={tab === "artists"}>
          Artistas
        </button>
        <button onClick={() => setTab("genres")} disabled={tab === "genres"}>
          Géneros
        </button>

        {role !== "admin" && (
          <button onClick={() => setTab("purchases")} disabled={tab === "purchases"}>
            Mis compras
          </button>
        )}
      </div>

      {/* ADMIN CREATE */}
      {tab === "tracks" && token && role === "admin" && (
        <div
          style={{
            border: "1px solid #333",
            borderRadius: 12,
            padding: 14,
            marginBottom: 16,
          }}
        >
          <h3>Admin: Crear canción</h3>

          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <input
              placeholder="Nombre canción"
              value={createName}
              onChange={(e) => setCreateName(e.target.value)}
              style={{ padding: 10, flex: 2 }}
            />

            <input
              type="number"
              step="0.01"
              placeholder="Precio"
              value={createPrice}
              onChange={(e) => setCreatePrice(e.target.value)}
              style={{ padding: 10, width: 140 }}
            />

            <select
              value={createArtistId}
              onChange={(e) => {
                setCreateArtistId(e.target.value);
                setCreateAlbumId("");
              }}
              style={{ padding: 10, flex: 2 }}
            >
              <option value="">-- Artista --</option>
              {adminArtists.map((a) => (
                <option key={a.ArtistId} value={a.ArtistId}>
                  {artistLabel(a)}
                </option>
              ))}
            </select>

            <select
              value={createGenreId}
              onChange={(e) => setCreateGenreId(e.target.value)}
              style={{ padding: 10, flex: 1 }}
            >
              <option value="">-- Género (opcional) --</option>
              {adminGenres.map((g) => (
                <option key={g.GenreId} value={g.GenreId}>
                  {genreLabel(g)}
                </option>
              ))}
            </select>
          </div>

          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 10 }}>
            <select
              value={albumMode}
              onChange={(e) => setAlbumMode(e.target.value)}
              style={{ padding: 10, width: 230 }}
            >
              <option value="existing">Usar álbum existente</option>
              <option value="new">Crear nuevo álbum</option>
            </select>

            {albumMode === "existing" ? (
              <select
                value={createAlbumId}
                onChange={(e) => setCreateAlbumId(e.target.value)}
                style={{ padding: 10, flex: 2 }}
                disabled={!createArtistId}
              >
                <option value="">
                  {createArtistId
                    ? adminAlbums.length
                      ? "-- Álbum --"
                      : "No hay álbumes para este artista"
                    : "Selecciona artista primero"}
                </option>

                {adminAlbums.map((al) => (
                  <option key={al.AlbumId} value={al.AlbumId}>
                    {albumLabel(al)}
                  </option>
                ))}
              </select>
            ) : (
              <input
                placeholder="Nombre del nuevo álbum"
                value={createAlbumTitle}
                onChange={(e) => setCreateAlbumTitle(e.target.value)}
                style={{ padding: 10, flex: 2 }}
                disabled={!createArtistId}
              />
            )}

            <button onClick={adminCreateTrack} style={{ padding: "10px 14px" }}>
              Crear
            </button>
          </div>
        </div>
      )}

      {/* TRACKS TAB */}
      {tab === "tracks" && (
        <div
          style={{
            border: "1px solid #333",
            borderRadius: 12,
            padding: 14,
            marginBottom: 16,
          }}
        >
          <h3>Tracks</h3>
          <div style={{ display: "flex", gap: 10, marginBottom: 10 }}>
            <input
              value={trackQuery}
              onChange={(e) => setTrackQuery(e.target.value)}
              style={{ flex: 1, padding: 10 }}
            />
            <button onClick={loadTracks} style={{ padding: "8px 12px" }}>
              {loadingTracks ? "Cargando..." : "Buscar"}
            </button>
          </div>

          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "1px solid #333" }}>
                <th style={{ padding: 10 }}>Track</th>
                <th style={{ padding: 10 }}>Artist</th>
                <th style={{ padding: 10 }}>Genre</th>
                <th style={{ padding: 10 }}>Price</th>
                <th style={{ padding: 10, textAlign: "right" }}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {tracks.map((t) => {
                const alreadyBought = purchasedIds.has(t.TrackId);

                return (
                  <tr key={t.TrackId} style={{ borderBottom: "1px solid #222" }}>
                    <td style={{ padding: 10 }}>
                      <div style={{ fontWeight: 600 }}>{t.TrackName}</div>
                      <div style={{ fontSize: 12, opacity: 0.75 }}>{t.AlbumTitle}</div>
                    </td>
                    <td style={{ padding: 10 }}>{t.ArtistName}</td>
                    <td style={{ padding: 10 }}>{t.GenreName || "-"}</td>
                    <td style={{ padding: 10 }}>{t.UnitPrice}</td>

                    <td style={{ padding: 10, textAlign: "right" }}>
                      {token && role === "admin" && (
                        <>
                          {editingId === t.TrackId ? (
                            <>
                              <input
                                value={editName}
                                onChange={(e) => setEditName(e.target.value)}
                                style={{ width: 220, padding: 6, marginRight: 8 }}
                                placeholder="Nuevo nombre"
                              />
                              <input
                                type="number"
                                step="0.01"
                                value={editPrice}
                                onChange={(e) => setEditPrice(e.target.value)}
                                style={{ width: 110, padding: 6, marginRight: 8 }}
                                placeholder="Precio"
                              />
                              <button onClick={() => adminSaveEdit(t.TrackId)}>Guardar</button>
                              <button
                                onClick={() => setEditingId(null)}
                                style={{ marginLeft: 6 }}
                              >
                                Cancelar
                              </button>
                            </>
                          ) : (
                            <>
                              <button
                                onClick={() => {
                                  setEditingId(t.TrackId);
                                  setEditName(t.TrackName);
                                  setEditPrice(String(t.UnitPrice));
                                }}
                              >
                                Editar
                              </button>
                              <button
                                onClick={() => adminDeleteTrack(t.TrackId)}
                                style={{ marginLeft: 8 }}
                              >
                                Eliminar
                              </button>
                            </>
                          )}
                        </>
                      )}

                      {token && role === "user" && (
                        <>
                          {alreadyBought ? (
                            <button disabled style={{ opacity: 0.6 }}>
                              Comprada ✅
                            </button>
                          ) : (
                            <button onClick={() => buy(t.TrackId)}>Comprar</button>
                          )}
                        </>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* ARTISTS TAB */}
      {tab === "artists" && (
        <div
          style={{
            border: "1px solid #333",
            borderRadius: 12,
            padding: 14,
            marginBottom: 16,
          }}
        >
          <h3>Artistas (Álbumes / Canciones)</h3>
          <div style={{ display: "flex", gap: 10, marginBottom: 10 }}>
            <input
              value={artistQuery}
              onChange={(e) => setArtistQuery(e.target.value)}
              placeholder="Buscar artista..."
              style={{ flex: 1, padding: 10 }}
            />
            <button onClick={searchArtistsStats}>
              {loadingArtists ? "..." : "Buscar"}
            </button>
          </div>

          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "1px solid #333" }}>
                <th style={{ padding: 10 }}>Artista</th>
                <th style={{ padding: 10 }}>Álbumes</th>
                <th style={{ padding: 10 }}>Canciones</th>
              </tr>
            </thead>
            <tbody>
              {artistStats.map((a) => (
                <tr key={a.ArtistId} style={{ borderBottom: "1px solid #222" }}>
                  <td style={{ padding: 10 }}>{a.ArtistName}</td>
                  <td style={{ padding: 10 }}>{a.AlbumCount}</td>
                  <td style={{ padding: 10 }}>{a.TrackCount}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* GENRES TAB */}
      {tab === "genres" && (
        <div
          style={{
            border: "1px solid #333",
            borderRadius: 12,
            padding: 14,
            marginBottom: 16,
          }}
        >
          <h3>Géneros (# Canciones)</h3>
          <div style={{ display: "flex", gap: 10, marginBottom: 10 }}>
            <input
              value={genreQuery}
              onChange={(e) => setGenreQuery(e.target.value)}
              placeholder="Buscar género..."
              style={{ flex: 1, padding: 10 }}
            />
            <button onClick={searchGenresStats}>
              {loadingGenres ? "..." : "Buscar"}
            </button>
          </div>

          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "1px solid #333" }}>
                <th style={{ padding: 10 }}>Género</th>
                <th style={{ padding: 10 }}>Canciones</th>
              </tr>
            </thead>
            <tbody>
              {genreStats.map((g) => (
                <tr key={g.GenreId} style={{ borderBottom: "1px solid #222" }}>
                  <td style={{ padding: 10 }}>{g.GenreName}</td>
                  <td style={{ padding: 10 }}>{g.TrackCount}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* PURCHASES TAB */}
      {tab === "purchases" && role !== "admin" && (
        <div
          style={{
            border: "1px solid #333",
            borderRadius: 12,
            padding: 14,
            marginBottom: 16,
          }}
        >
          <h3>Mis compras</h3>

          {!token ? (
            <div style={{ opacity: 0.75 }}>Inicia sesión para ver tus compras.</div>
          ) : (
            <>
              <button onClick={loadPurchases} style={{ marginBottom: 10 }}>
                {loadingPurchases ? "Cargando..." : "Refrescar"}
              </button>

              {purchases.length === 0 ? (
                <div style={{ opacity: 0.7 }}>Aún no tienes compras.</div>
              ) : (
                <ul>
                  {purchases.map((pp) => (
                    <li key={`${pp.InvoiceId}-${pp.TrackId}`}>
                      <b>{pp.TrackName}</b> — {pp.ArtistName} · {pp.GenreName} · qty{" "}
                      {pp.Quantity} · total {pp.LineTotal}
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
