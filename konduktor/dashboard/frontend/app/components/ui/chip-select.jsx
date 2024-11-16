import { useState } from 'react';
import Box from '@mui/material/Box';
import OutlinedInput from '@mui/material/OutlinedInput';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import FormControl from '@mui/material/FormControl';
import Select from '@mui/material/Select';
import Chip from '@mui/material/Chip';


export default function ChipSelect(props) {

    const handleChange = (event) => {
            const {
            target: { value },
        } = event;
        props.setSelectedNamespaces(
            // On autofill we get a stringified value.
            typeof value === 'string' ? value.split(',') : value,
        );
    };

  return (
    <FormControl className='flex w-3/4' >
        <InputLabel id="demo-multiple-chip-label" sx={{ 
            lineHeight: 1.2, 
            fontSize: '14px', 
            color: 'gray', 
            "&.Mui-focused": {
                color: 'gray'
            } 
        }} >
            Namespace(s)
        </InputLabel>
        <Select
            labelId="demo-multiple-chip-label"
            id="demo-multiple-chip"
            multiple
            value={props.selectedNamespaces}
            onChange={handleChange}
            input={<OutlinedInput id="select-multiple-chip" label="Namespace(s)" />}
            sx={{ 
                minHeight: '48px',
                borderRadius: '0.375rem',
                '.MuiSelect-select': {
                    height: 'auto',
                    p: '8px',
                },
                '.MuiOutlinedInput-notchedOutline': {
                    borderColor: '#e5e7eb',
                },
                '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                    borderColor: '#e5e7eb',
                },
                '&:hover .MuiOutlinedInput-notchedOutline': {
                    borderColor: '#e5e7eb',
                },
            }}
            renderValue={(selected) => (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.3 }}>
                    {selected.map((value) => (
                        <Chip sx={{ fontSize: '12px', maxHeight: '24px', borderRadius: '4px' }} key={value} label={value} />
                    ))}
                </Box>
            )}
        >
          {props.namespaces.map((choice) => (
            <MenuItem
              key={choice}
              value={choice}
            >
              {choice}
            </MenuItem>
          ))}
        </Select>
    </FormControl>
  );
}