import { useState } from 'react'
import './App.css'

import NavTabs from './components/NavTabs'
import LogsMain from './components/LogsMain'
import MetricsMain from './components/MetricsMain'
import JobsMain from './components/JobsMain'

function App() {

  const [tab, setTab] = useState(0)

  const handleTabChange = (event, newValue) => {
    setTab(newValue)
  }

  return (
    <div className='flex w-screen h-screen p-2 flex-col'>
      <NavTabs tab={tab} handleTabChange={handleTabChange} />
      {tab === 0 ?
        <MetricsMain />
      :
        null 
      }
      {tab === 1 ?
        <LogsMain />
      :
        null 
      }
      {tab === 2 ?
        <JobsMain />
      :
        null 
      }
    </div>
  )
}

export default App
