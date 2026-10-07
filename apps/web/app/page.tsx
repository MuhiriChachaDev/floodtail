/**
 * Empty frontend scaffold — no product UI yet.
 * Modelling is served by FastAPI at /docs and /v1/*.
 */
export default function HomePage() {
  return (
    <main style={{ fontFamily: "system-ui", padding: "2rem", maxWidth: 640 }}>
      <h1>FLOODTAIL</h1>
      <p>
        Frontend scaffold only. No underwriting UI has been implemented yet.
      </p>
      <p>
        Use the API: <code>http://localhost:8000/docs</code>
      </p>
      <p>
        Health: <code>http://localhost:8000/v1/health</code>
      </p>
    </main>
  );
}
