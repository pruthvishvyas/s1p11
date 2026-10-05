import { createContext, useContext, useState } from 'react';

const Ctx = createContext({ segment: null, setSegment: () => {} });

export function OutcomeProvider({ children }) {
  const [segment, setSegment] = useState(null);
  return <Ctx.Provider value={{ segment, setSegment }}>{children}</Ctx.Provider>;
}

export const useOutcome = () => useContext(Ctx);
