export default function Settings() {
  return (
    <div className="page">
      <header>
        <p className="eyebrow">Tools</p>
        <h1>Settings</h1>
        <p>Creative preferences and browser-safe workspace operations.</p>
      </header>
      <div className="settings-grid">
        <section className="panel">
          <h2>AI Models</h2>
          <p>
            Task routing and credentials are configured privately by the hosted
            application. Secrets are never displayed here.
          </p>
          <label>
            Preferred writing style
            <textarea placeholder="Optional author guidance" />
          </label>
          <label>
            Forbidden tendencies
            <textarea placeholder="Words, habits, or patterns to avoid" />
          </label>
          <button className="primary-button">Save Creative Settings</button>
        </section>
        <section className="panel">
          <h2>Appearance</h2>
          <label>
            Interface density
            <select>
              <option>Compact</option>
              <option>Comfortable</option>
            </select>
          </label>
          <label>
            Draft font
            <select>
              <option>Literary serif</option>
              <option>System sans-serif</option>
            </select>
          </label>
        </section>
        <section className="panel">
          <h2>Backups & Exports</h2>
          <p>
            Hosted PostgreSQL, private storage, and export history remain
            managed by existing services.
          </p>
          <a className="secondary-button" href="/archives/">
            Open Archive Tools
          </a>
        </section>
      </div>
    </div>
  );
}
