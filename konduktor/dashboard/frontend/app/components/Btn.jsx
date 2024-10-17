'use client'

import React from 'react'
import { Button } from "./ui/button"

function Btn() {

  return (
    <div className='flex gap-4'>
      <Button onClick={() => window.open('http://localhost:3000/dashboards', '_blank')}>
        View in Grafana
      </Button>
    </div>
  )
}

export default Btn