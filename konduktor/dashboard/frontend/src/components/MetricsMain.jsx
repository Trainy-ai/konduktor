import {useEffect} from 'react'
import Btn from './Btn'

function MetricsMain() {

  useEffect(() => {

    console.log('fetching')
    console.log('updated non 1.1')

    // Fetch data from backend
    const fetchData = async () => {
      try {
        const response = await fetch('http://backend.default.svc.cluster.local:5001/ping');
        const data = await response.json();
        console.log(JSON.stringify(data))
      } catch (error) {
        console.error('Error fetching from backend:', error);
      }
    };

    fetchData();
  }, []);

  return (
    <div className='flex w-full h-full mt-2'>
        <Btn />
    </div>
  )
}

export default MetricsMain