import React from 'react'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select"

function SelectBtn() {
  return (
    <div className="flex flex-col space-y-1.5">
        <Select>
            <SelectTrigger id="framework" className='tracking-wide mr-2'>
                <SelectValue placeholder="View In Grafana" />
            </SelectTrigger>
            <SelectContent position="popper">
                <SelectItem value="1">Core Dashboard</SelectItem>
                <SelectItem value="2">Ray Data Dashboard</SelectItem>
            </SelectContent>
        </Select>
    </div>
  )
}

export default SelectBtn