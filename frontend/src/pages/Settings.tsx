export default function Settings() {
  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Settings</h2>
        <p className="text-sm text-[var(--color-text-secondary)]">
          Configure your ArXiv Graph Explorer preferences.
        </p>
      </div>

      <div className="bg-[var(--color-card)] rounded-xl border border-[var(--color-border)] p-6 space-y-6">
        {/* Appearance */}
        <div>
          <h3 className="font-semibold mb-4">Appearance</h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium">Dark Mode</div>
                <div className="text-xs text-[var(--color-text-secondary)]">
                  Switch between light and dark themes
                </div>
              </div>
              <button className="w-11 h-6 bg-gray-200 rounded-full relative transition-colors">
                <div className="w-5 h-5 bg-white rounded-full absolute left-0.5 top-0.5 shadow transition-transform" />
              </button>
            </div>
          </div>
        </div>

        <hr className="border-[var(--color-border)]" />

        {/* Analysis */}
        <div>
          <h3 className="font-semibold mb-4">Analysis</h3>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Max References</label>
              <p className="text-xs text-[var(--color-text-secondary)] mb-2">
                Maximum number of references to analyze
              </p>
              <input
                type="number"
                defaultValue={20}
                className="w-32 px-3 py-2 rounded-lg border border-[var(--color-border)] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
              />
            </div>
            <div>
              <label className="text-sm font-medium">Confidence Threshold</label>
              <p className="text-xs text-[var(--color-text-secondary)] mb-2">
                Minimum confidence for extracted relationships
              </p>
              <input
                type="number"
                defaultValue={0.5}
                step={0.1}
                min={0}
                max={1}
                className="w-32 px-3 py-2 rounded-lg border border-[var(--color-border)] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
              />
            </div>
          </div>
        </div>

        <hr className="border-[var(--color-border)]" />

        {/* API */}
        <div>
          <h3 className="font-semibold mb-4">API Configuration</h3>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Backend URL</label>
              <p className="text-xs text-[var(--color-text-secondary)] mb-2">
                URL of the kgraph backend API
              </p>
              <input
                type="text"
                defaultValue="http://localhost:8000"
                className="w-full px-3 py-2 rounded-lg border border-[var(--color-border)] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
