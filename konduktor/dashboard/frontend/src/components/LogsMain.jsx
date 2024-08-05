import { useState, useEffect } from 'react'

import NavTabs2 from './NavTabs2'

import { Input } from "@/components/ui/input"
import { FaSearch } from 'react-icons/fa';

function LogsMain() {

    const [tab, setTab] = useState(0)
    const [logsData, setLogsData] = useState([])

    const handleTabChange = (event, newValue) => {
      setTab(newValue)
    }

    const fetchData = async () => {
        try {
            const response = await fetch(`http://127.0.0.1:5000/logs`);
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            const data = await response.json();
            setLogsData(data)
        } catch (error) {
            console.error("Fetch error:", error);
        }
    }

    useEffect(() => {
        fetchData()
    }, [])

    return (
        <div className='flex w-full h-full flex-col mt-2 p-8'>
            <NavTabs2 tab={tab} handleTabChange={handleTabChange} />
            <div className='flex w-full my-4 py-4 justify-center bg-slate-50 rounded-md border-2'>
                <div className="relative w-full md:w-1/4 min-w-[250px] mx-8 md:mx-0 flex justify-center items-center">
                    <span className="absolute left-3 text-gray-500">
                        <FaSearch />
                    </span>
                    <Input
                        className="pl-10 w-full"
                        placeholder="Search"
                    />
                </div>
            </div>
            {tab === 0 ?
                <div className='flex w-full bg-white h-full py-2 justify-center bg-slate-50 rounded-md border-2 max-h-[450px] box-border'>
                    <div className='w-full bg-white flex flex-col overflow-y-scroll box-border'>
                        {logsData && logsData.map((data, index) => (
                            <div key={index} className='py-1 px-2 flex flex-row box-border'>
                                <div className='w-36 min-w-36 max-w-36'>
                                    <p className='text-gray-500 text-[12px]'>{data.timestamp}</p>
                                </div>
                                <div>
                                    <p className="text-gray-900 text-[12px] leading-4">{data.log}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            :
                null
            }
        </div>
    )
}

export default LogsMain