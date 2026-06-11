import { useState, useEffect } from 'react';

export interface WindowLayout {
    x: number;
    y: number;
    width: number;
    height: number;
}

export const useAdaptiveLayout = () => {
    const [screenSize, setScreenSize] = useState({ width: window.innerWidth, height: window.innerHeight });

    useEffect(() => {
        const handleResize = () => setScreenSize({ width: window.innerWidth, height: window.innerHeight });
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    const getLayout = (type: string): WindowLayout => {
        const { width, height } = screenSize;
        const isSmall = width < 1024;
        
        switch (type) {
            case 'terminal':
                return {
                    x: 40,
                    y: 80,
                    width: isSmall ? width - 80 : 700,
                    height: isSmall ? (height / 2) - 100 : 500
                };
            case 'browser':
                return {
                    x: isSmall ? 40 : 760,
                    y: isSmall ? (height / 2) + 20 : 80,
                    width: isSmall ? width - 80 : width - 800,
                    height: isSmall ? (height / 2) - 140 : height - 200
                };
            case 'monitor':
                return {
                    x: 40,
                    y: height - 420,
                    width: 700,
                    height: 300
                };
            case 'market':
                return {
                    x: width - 500,
                    y: 80,
                    width: 460,
                    height: 300
                };
            case 'portfolio':
                return {
                    x: width - 500,
                    y: 400,
                    width: 460,
                    height: height - 520
                };
            default:
                return { x: 100, y: 100, width: 800, height: 600 };
        }
    };

    return { screenSize, getLayout };
};
