'use client';

import { useState, useEffect } from 'react';
import { usePathname } from 'next/navigation';
import Link from 'next/link'; // Import Link from Next.js for client-side navigation
import Box from '@mui/material/Box';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';

function NavTabs() {
  const pathname = usePathname();
  const [tabValue, setTabValue] = useState(undefined);

  useEffect(() => {
    if (!pathname) return;

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
  };

  return (
    <Box sx={{ width: '100%' }}>
      {tabValue !== undefined ? (
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
          <Tab
            component={Link}
            href="/"
            label="Metrics"
            sx={{ fontWeight: 'bold', fontFamily: 'Poppins' }}
          />
          <Tab
            component={Link}
            href="/logs"
            label="Logs"
            sx={{ fontWeight: 'bold', fontFamily: 'Poppins' }}
          />
          <Tab
            component={Link}
            href="/jobs"
            label="Jobs"
            sx={{ fontWeight: 'bold', fontFamily: 'Poppins' }}
          />
        </Tabs>
      ) : null}
    </Box>
  );
}

export default NavTabs;
