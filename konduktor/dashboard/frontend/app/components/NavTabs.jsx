'use client';

import { useState, useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation'; // usePathname instead of useRouter directly
import Box from '@mui/material/Box';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';

function NavTabs() {
  const router = useRouter();
  const pathname = usePathname(); // Using usePathname to get the current route

  const [tabValue, setTabValue] = useState(undefined);

  // Update the tabValue based on the current path
  useEffect(() => {
    if (!pathname) return; // Ensure pathname is available before proceeding

    if (pathname === '/') {
      setTabValue(0);
    } else if (pathname === '/logs') {
      setTabValue(1);
    } else if (pathname === '/jobs') {
      setTabValue(2);
    }
  }, [pathname]);

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
    if (newValue === 0) {
      router.push('/');
    } else if (newValue === 1) {
      router.push('/logs');
    } else if (newValue === 2) {
      router.push('/jobs');
    }
  };

  return (
    <Box sx={{ width: '100%' }}>
      {tabValue !== undefined ?
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          sx={{
            borderBottom: '2px solid rgb(229 231 235) !important',
            '& .MuiTabs-indicator': {
              backgroundColor: 'rgb(75 85 99) !important',
            },
            '& .MuiTab-root': {
              color: 'rgb(107 114 128) !important',
            },
            '& .Mui-selected': {
              color: 'black !important',
            },
          }}
        >
          <Tab label="Metrics" sx={{ fontWeight: 'bold', fontFamily: 'Poppins' }} />
          <Tab label="Logs" sx={{ fontWeight: 'bold', fontFamily: 'Poppins' }} />
          <Tab label="Jobs" sx={{ fontWeight: 'bold', fontFamily: 'Poppins' }} />
        </Tabs>
      :
        null
      }
    </Box>
  );
}

export default NavTabs;
