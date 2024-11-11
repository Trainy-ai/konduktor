import React from 'react'
import {
    NavigationMenu,
    NavigationMenuContent,
    NavigationMenuIndicator,
    NavigationMenuItem,
    NavigationMenuLink,
    NavigationMenuList,
    NavigationMenuTrigger,
    NavigationMenuViewport,
} from "./ui/navigation-menu"
import Box from '@mui/material/Box';  

function NavMenu() {
  return (
    <NavigationMenu>
        <NavigationMenuList>
            <NavigationMenuItem>
                <NavigationMenuTrigger>Item One</NavigationMenuTrigger>
                <NavigationMenuContent>
                    <Box sx={{ width: '600px', height: '300px', display: 'flex', justifyContent: 'center', p: '16px' }}>
                        <NavigationMenuLink>Link</NavigationMenuLink>
                    </Box>
                </NavigationMenuContent>
            </NavigationMenuItem>
            <NavigationMenuItem>
                <NavigationMenuTrigger>Item Two</NavigationMenuTrigger>
                <NavigationMenuContent>
                    <Box sx={{ width: '300px', height: '300px', display: 'flex', justifyContent: 'center' }}>
                        <NavigationMenuLink>Link</NavigationMenuLink>
                    </Box>
                </NavigationMenuContent>
            </NavigationMenuItem>
        </NavigationMenuList>
    </NavigationMenu>
  )
}

export default NavMenu