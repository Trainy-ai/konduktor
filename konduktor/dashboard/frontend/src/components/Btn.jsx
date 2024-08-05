import React from 'react'
import { Button } from "@/components/ui/button"

function Btn() {
  return (
    <Button onClick={() => window.open('https://snapshots.raintank.io/dashboard/snapshot/qJUzCCb4nLspDAJfGKd4EexUKJEmvEvu?orgId=0', '_blank')}>
        View in Grafana
    </Button>
  )
}

export default Btn