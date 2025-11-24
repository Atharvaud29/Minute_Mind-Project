// export default function Summary() {
//   return (
//     <div className="space-y-4">
//       <h1 className="text-2xl font-semibold">Summary</h1>
//       <div className="grid md:grid-cols-2 gap-4">
//         <div className="card p-4">
//           <h3 className="font-medium mb-2">Meeting Highlights</h3>
//           <p className="text-sm text-gray-600">No data yet.</p>
//         </div>
//         <div className="card p-4">
//           <h3 className="font-medium mb-2">Key Decisions</h3>
//           <p className="text-sm text-gray-600">No data yet.</p>
//         </div>
//       </div>
//     </div>
//   )
// }

// summary.jsx
import { useState, useEffect } from 'react';

export default function Summary() {
  const [highlights, setHighlights] = useState([]);
  const [decisions, setDecisions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('http://127.0.0.1:5000/api/summary')  // ✅ absolute URL to Flask
      .then(response => {
        if (!response.ok) throw new Error('Network response was not ok');
        return response.json();
      })
      .then(data => {
        setHighlights(data.highlights || []);
        setDecisions(data.decisions || []);
        setLoading(false);
      })
      .catch(error => {
        console.error('Error fetching summary data:', error);
        setLoading(false);
      });
  }, []);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Summary</h1>
      <div className="grid md:grid-cols-2 gap-4">
        <div className="card p-4">
          <h3 className="font-medium mb-2">Meeting Highlights</h3>
          {loading ? (
            <p className="text-sm text-gray-600">Loading...</p>
          ) : highlights.length > 0 ? (
            <ul className="list-disc list-inside space-y-1">
              {highlights.map((item, index) => (
                <li key={index} className="text-sm text-gray-600">{item}</li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-600">No data yet.</p>
          )}
        </div>

        <div className="card p-4">
          <h3 className="font-medium mb-2">Key Decisions</h3>
          {loading ? (
            <p className="text-sm text-gray-600">Loading...</p>
          ) : decisions.length > 0 ? (
            <ul className="list-disc list-inside space-y-1">
              {decisions.map((item, index) => (
                <li key={index} className="text-sm text-gray-600">{item}</li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-600">No data yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}