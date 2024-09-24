import { useState, useEffect, useRef } from 'react'

import NavTabs2 from './NavTabs2'

import { Input } from "@/components/ui/input"
import { FaSearch } from 'react-icons/fa';

import { io } from 'socket.io-client';

function LogsMain() {

    const [tab, setTab] = useState(0)
    const [logsData, setLogsData] = useState([])
    const [isAtBottom, setIsAtBottom] = useState(true);  // Track if user is at the bottom
    const logContainerRef = useRef(null);
    const [searchQuery, setSearchQuery] = useState('')

    const handleTabChange = (event, newValue) => {
      setTab(newValue)
    }

    // Check if user is at the bottom of the log container
    const handleScroll = () => {
        if (logContainerRef.current) {
            const { scrollTop, scrollHeight, clientHeight } = logContainerRef.current
            const isUserAtBottom = scrollTop + clientHeight >= scrollHeight
            setIsAtBottom(isUserAtBottom)
        }
    }

    const handleSearchChange = (event) => {
        setSearchQuery(event.target.value)
    }

    const filteredLogs = logsData.filter(log => 
        log.log.toLowerCase().includes(searchQuery.toLowerCase()) ||
        log.timestamp.toLowerCase().includes(searchQuery.toLowerCase())
    )

    useEffect(() => {
        console.log('here')
        const socket = io('http://localhost:5001', {
            transports: ['websocket', 'polling'], 
        });
    
        socket.on('connect', () => {
            console.log('Connected to server');
        });
    
        socket.on('disconnect', () => {
            console.log('Disconnected from server');
        });
    
        socket.on('log_data', (data) => {
            setLogsData((prevLogs) => [...prevLogs, ...data])
            console.log(data)
        })
    
        return () => {
            socket.disconnect();
        };
    }, []);

    useEffect(() => {
        if (isAtBottom && logContainerRef.current) {
            logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
        }
    }, [logsData, isAtBottom]);

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
                        value={searchQuery}
                        onChange={handleSearchChange}
                    />
                </div>
            </div>
            {tab === 0 ?
                <div className='flex w-full bg-white h-full py-2 justify-center bg-slate-50 rounded-md border-2 max-h-[450px] box-border'>
                    <div ref={logContainerRef} onScroll={handleScroll} className='w-full bg-white flex flex-col overflow-y-scroll box-border'>
                        {filteredLogs.map((data, index) => (
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
            : null}
        </div>
    )
}

export default LogsMain