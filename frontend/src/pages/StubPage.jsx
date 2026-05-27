export default function StubPage({ title, description }) {
  return (
    <div className="flex min-h-[400px] flex-col items-center justify-center rounded-lg border border-dashed border-zinc-800 bg-zinc-900/20 p-12 text-center">
      <h1 className="text-xl font-semibold text-zinc-300">{title}</h1>
      <p className="mt-2 max-w-md text-sm text-zinc-500">{description}</p>
      <span className="mt-4 rounded border border-zinc-700 px-3 py-1 text-xs text-zinc-600">Coming soon</span>
    </div>
  )
}
