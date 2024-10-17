import "./globals.css";

import Btn from "./components/Btn";
import Grafana from "./components/Grafana";

export default function Home() {

  return (
    <div className='flex w-screen h-screen p-2 flex-col'>
      <Grafana />
    </div>
  );
}
