'use client'

import { useEffect, useState, useRef } from 'react';
import { io } from 'socket.io-client';
import { Input } from "./ui/input";
import { FaSearch } from 'react-icons/fa';

const SocketComponent = () => {

    const [logsData, setLogsData] = useState([]);
    const [isAtBottom, setIsAtBottom] = useState(true);  // Track if user is at the bottom
    const logContainerRef = useRef(null);
    const [searchQuery, setSearchQuery] = useState('')

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
        // Connect to Next.js Socket.IO server
        const socket = io('http://localhost:5173');  // The Next.js server's address

        socket.on('connect', () => {
            console.log('Connected to Next.js Socket.IO server');
        });

        socket.on('log_data', (data) => {
            setLogsData((prevLogs) => [...prevLogs, ...data]);
            console.log('Received log data:', data);
        });

        socket.on('disconnect', () => {
            console.log('Disconnected from Next.js Socket.IO server');
        });

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
        </div>
    );
};

export default SocketComponent;
