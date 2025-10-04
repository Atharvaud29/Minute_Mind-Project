export default function Summary() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Summary</h1>
      <div className="grid md:grid-cols-2 gap-4">
        <div className="card p-4">
          <h3 className="font-medium mb-2">Meeting Highlights</h3>
          <p className="text-sm text-gray-600">No data yet.</p>
        </div>
        <div className="card p-4">
          <h3 className="font-medium mb-2">Key Decisions</h3>
          <p className="text-sm text-gray-600">No data yet.</p>
        </div>
      </div>
    </div>
  )
}


