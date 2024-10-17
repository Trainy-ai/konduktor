// Server Component
export default async function MetricsData() {

  const backendUrl = process.env.NODE_ENV === 'development'
    ? 'http://127.0.0.1:5000' // Development API
    : 'http://backend.konduktor-dashboard.svc.cluster.local:5001' // Production API

  // Fetch data from backend
  const fetchData = async () => {
    try {
      const response = await fetch(`${backendUrl}/ping`, {cache: 'no-store'});
      const data = await response.json();
      console.log(JSON.stringify(data))
      return JSON.stringify(data)
    } catch (error) {
      console.error('Error fetching from backend:', error);
    }
  };

  const data = await fetchData()
  
  return (
    <div className='flex w-full h-full flex-col mt-2 p-8'>
      <h2>{data}</h2>
    </div>
  );
}
  