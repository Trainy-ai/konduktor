import { useState, useEffect } from 'react'
import { DataGrid, GridActionsCellItem } from '@mui/x-data-grid';
import DeleteIcon from '@mui/icons-material/DeleteOutlined';


function JobsTable() {

    const [jobsData, setJobsData] = useState([])
    const [update, setUpdate] = useState(false)

    const [paginationModel, setPaginationModel] = useState({
        pageSize: 10,
        page: 0,
    });

    const fetchData = async () => {
        try {
            const response = await fetch(`http://backend.default.svc.cluster.local:5001/jobs`);
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            const data = await response.json();
            console.log(`Fetching jobs data: ${JSON.stringify(data)}`)
            setJobsData(data)
        } catch (error) {
            console.error("Fetch error:", error);
        }
    }

    const updatePriority = async (name, namespace, priority, priority_class_name) => {
        try {
            const response = await fetch('http://backend.default.svc.cluster.local:5001/updatePriority', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ name, namespace, priority, priority_class_name })
            });
        } catch (error) {
            console.error("Fetch error:", error);
        }
    }

    const handleDelete = async (row) => {

        const { name, namespace } = row;

        try {
            const response = await fetch('http://backend.default.svc.cluster.local:5001/deleteJob', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ name, namespace })
            });

            setUpdate(!update)

        } catch (error) {
            console.error("Fetch error:", error);
        }

        return
    };

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
            headerName: 'Delete',
            width: 70,
            cellClassName: 'actions',
            getActions: (params) => {
      
              return [
                    <GridActionsCellItem
                        icon={<DeleteIcon />}
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
            await updatePriority(updatedRow.name, updatedRow.namespace, updatedRow.priority, "")
        } catch (error) {
            console.error("Fetch error:", error);
        }

        return updatedRow
    };

    useEffect(() => {
        fetchData()
    }, [update])

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
                rows={jobsData}
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

export default JobsTable