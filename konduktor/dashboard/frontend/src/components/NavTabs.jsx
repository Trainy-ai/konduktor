import { useState } from 'react'
import Box from '@mui/material/Box';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';


function NavTabs(props) {
  
    return (
      <Box sx={{ width: '100%' }} >
        <Tabs value={props.tab} onChange={props.handleTabChange} sx={{ 
          borderBottom: '2px solid rgb(229 231 235) !important',
          '& .MuiTabs-indicator': {
            backgroundColor: 'rgb(75 85 99) !important', // Change the indicator color
          },
          '& .MuiTab-root': {
            color: 'rgb(107 114 128) !important', // Change the default text color
          },
          '& .Mui-selected': {
            color: 'black !important',
          },
        }} >
          <Tab label="Metrics" sx={{ fontWeight: 'bold', fontFamily: 'Poppins' }} />
          <Tab label="Logs" sx={{ fontWeight: 'bold', fontFamily: 'Poppins' }} />
          <Tab label="Jobs" sx={{ fontWeight: 'bold', fontFamily: 'Poppins' }} />
        </Tabs>
      </Box>
    );
}

export default NavTabs