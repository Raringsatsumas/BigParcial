import { useEffect, useState } from "react";

export default function App() {
  const [apiStatus, setApiStatus] = useState("Cargando...");

  useEffect(() => {
    const apiUrl = import.meta.env.VITE_API_URL;

    fetch(`${apiUrl}/health`)
      .then((r) => r.json())
      .then((data) => setApiStatus(data.status))
      .catch(() => setApiStatus("ERROR (no conecta al backend)"));
  }, []);

  return (
    <div style={{ padding: 24, fontFamily: "sans-serif" }}>
      <h1>Chinook Store</h1>
      <p><b>API status:</b> {apiStatus}</p>
    </div>
  );
}
