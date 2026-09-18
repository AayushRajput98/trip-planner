/* Public config — the backend's URL is not a secret, so this is committed.
   The shared bearer token IS a secret and lives only in each editor's
   localStorage (entered once via the settings modal). */
const API_BASE = (location.hostname === "localhost" || location.hostname === "127.0.0.1")
  ? "http://127.0.0.1:8123"
  : "https://REPLACE-WITH-YOUR-RAILWAY-URL.up.railway.app";
