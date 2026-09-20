import { useState, useEffect } from 'react';

export type DeviceType = 'mobile' | 'tablet' | 'desktop';

function getDevice(): DeviceType {
  if (typeof window === 'undefined') return 'desktop';
  const w = window.innerWidth;
  if (w < 768) return 'mobile';
  if (w < 1024) return 'tablet';
  return 'desktop';
}

export function useDevice(): DeviceType {
  const [device, setDevice] = useState<DeviceType>(getDevice);

  useEffect(() => {
    const handler = () => setDevice(getDevice());
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, []);

  return device;
}
