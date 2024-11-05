'use client'

import { useEffect, useState, useRef } from 'react';
import { io } from 'socket.io-client';
import { Input } from "./ui/input";
import ChipSelect from "./ui/chip-select";
import { FaSearch } from 'react-icons/fa';

function LogsData() {

    const [logsData, setLogsData] = useState([]);
    const [namespaces, setNamespaces] = useState([]);
    const [selectedNamespaces, setSelectedNamespaces] = useState(['default']);
    const [isAtBottom, setIsAtBottom] = useState(true);  // Track if user is at the bottom
    const logContainerRef = useRef(null);
    const [searchQuery, setSearchQuery] = useState('')

    const socketRef = useRef(null);

    const fetchData = async () => {
        try {
            const response = await fetch(`/api/namespaces`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            const data = await response.json();
            setNamespaces(data)
            return
        } catch (error) {
            console.error('Error fetching from backend:', error);
            return
        }
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
        fetchData()
    }, []);

    useEffect(() => {
        // Create and store the socket instance only once
        if (!socketRef.current) {
          socketRef.current = io('http://localhost:5173');  // Connect to Next.js server
    
          socketRef.current.on('connect', () => {
            console.log('Connected to Next.js Socket.IO server');
          });
    
          socketRef.current.on('log_data', (data) => {
            setLogsData((prevLogs) => [...prevLogs, ...data]);
          });
    
          socketRef.current.on('disconnect', () => {
            console.log('Disconnected from Next.js Socket.IO server');
          });
        }
    
        // Clean up and disconnect the socket when the component unmounts
        return () => {
          if (socketRef.current) {
            socketRef.current.disconnect();
            socketRef.current = null;
            console.log('Socket disconnected on component unmount');
          }
        };
    }, []);
    
    // Emit selected namespaces whenever they change
    useEffect(() => {
        if (socketRef.current) {
          socketRef.current.emit('update_namespaces', selectedNamespaces);
        }
    }, [selectedNamespaces]);

    useEffect(() => {
        if (isAtBottom && logContainerRef.current) {
            logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
        }
    }, [logsData, isAtBottom]);

    return (
        <div className='flex w-full h-full flex-col px-8'>
            <div className='flex w-full my-4 py-4 justify-center gap-2'>
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
                <ChipSelect namespaces={namespaces} selectedNamespaces={selectedNamespaces} setSelectedNamespaces={setSelectedNamespaces} />
            </div>
            <div className='flex w-full bg-white h-full py-2 justify-center bg-slate-50 rounded-md border-2 max-h-[450px] box-border'>
                <div ref={logContainerRef} onScroll={handleScroll} className='w-full bg-white flex flex-col overflow-y-scroll box-border'>
                    {filteredLogs.map((data, index) => (
                        <div key={index} className='py-1 px-2 flex flex-row box-border'>
                            <div className='w-36 min-w-36 max-w-36'>
                                <p className='text-gray-500 text-[12px]'>{data.timestamp}</p>
                            </div>
                            <div className='flex justify-center mr-4'>
                                <div className='bg-[rgb(0,0,0,0.08)] rounded-[4px] px-2 h-[18px]'>
                                    <p className='text-gray-900 text-[12px]'>{data.namespace}</p>
                                </div>
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

export default LogsData
