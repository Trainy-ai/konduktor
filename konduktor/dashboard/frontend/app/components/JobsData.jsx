'use client'

import { useState, useEffect } from 'react'
import { DataGrid, GridActionsCellItem } from '@mui/x-data-grid';
import DeleteIcon from '@mui/icons-material/DeleteOutlined';


function JobsData() {

    const [data, setData] = useState([])

    const [paginationModel, setPaginationModel] = useState({
        pageSize: 10,
        page: 0,
    });

    const fetchData = async () => {
        try {
            const response = await fetch(`/api/jobs`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            const data = await response.json();
            setData(data)
            return data
        } catch (error) {
            console.error('Error fetching from backend:', error);
            return []
        }
    }

    const handleDelete = async (row) => {
        const { name, namespace } = row
        try {
            const response = await fetch(`/api/jobs`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ name, namespace })
            })
            const data2 = await response.json()

            // Optimistically remove the row from the state
            const newData = data.filter((job) => job.name !== name || job.namespace !== namespace);
            setData(newData);

        } catch (error) {
            console.error("Delete error:", error)
        }
    }
    
    const updatePriority = async (name, namespace, priority, priority_class_name) => {
        try {
            const response = await fetch(`/api/jobs`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ name, namespace, priority, priority_class_name })
            })
            const data = await response.json();
            return data
        } catch (error) {
            console.error("Put error:", error);
            return error
        }
    }

    const columns = [
        { 
            field: 'name', 
            headerName: 'NAME', 
            width: 200 
        },
        { 
            field: 'namespace', 
            headerName: 'NAMESPACE', 
            width: 120 
        },
        { 
            field: 'priority', 
            headerName: 'PRIORITY', 
            width: 100,
            type: 'number',
            editable: true,
        },
        { 
            field: 'status', 
            headerName: 'STATUS', 
            width: 120,
        },
        { 
            field: 'active', 
            headerName: 'ACTIVE', 
            width: 100,
        },
        { 
            field: 'created_at', 
            headerName: 'CREATED AT', 
            width: 160 
        },
        { 
            field: 'localQueueName', 
            headerName: 'CREATED BY', 
            width: 160 
        },
        { 
            field: 'order', 
            headerName: 'order', 
            width: 10,
            type: 'number',
        },
        {
            field: 'actions',
            type: 'actions',
            headerName: 'DELETE',
            width: 70,
            cellClassName: 'actions',
            getActions: (params) => {
      
              return [
                    <GridActionsCellItem
                        icon={<DeleteIcon />}
                        key={`delete-${params.row.id}`}
                        label="Delete"
                        onClick={() => handleDelete(params.row)}
                        color="inherit"
                    />,
              ];
            },
        },
    ];

    const processRowUpdate = async (newRow, oldRow) => {
        const updatedRow = { ...newRow };

        try {
            const res = await updatePriority(updatedRow.name, updatedRow.namespace, updatedRow.priority, "")
        } catch (error) {
            console.error("Fetch error:", error);
        }

        await fetchData()

        return oldRow
    };

    useEffect(() => {
        fetchData()
    }, [])


    return (
        <div className='flex w-full h-full flex-col p-8'>
            <DataGrid
                sx={{ 
                    color: 'black', 
                    fontFamily: 'Poppins',
                    bgcolor: 'white',
                    border: '2px solid hsl(var(--border))',
                    '& .MuiDataGrid-filler': {
                        backgroundColor: 'rgb(248 250 252)',
                    }, 
                    '& .MuiDataGrid-scrollbar--horizontal': {
                        left: 0
                    },
                    '--DataGrid-containerBackground': 'rgb(248 250 252)',
                }}
                rows={data}
                getRowId={(row) => row.id}
                columns={columns}
                paginationModel={paginationModel}
                onPaginationModelChange={setPaginationModel}
                processRowUpdate={processRowUpdate}
                editMode='row'
                sortModel={[
                    { field: 'order', sort: 'desc' },
                ]}
                initialState={{
                    columns: {
                      columnVisibilityModel: {
                        order: false,
                      },
                    },
                  }}
                checkboxSelection
                disableRowSelectionOnClick
                pageSizeOptions={[5, 10, 20, 50]}
            />
        </div>
    )
}

export default JobsData