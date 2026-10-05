import { createContext, useContext, useEffect, useState } from 'react';

const Ctx = createContext({ user: null, loading: true });

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // WARNING: without VITE_DEV_AUTH=true in .env, local dev has no Cloudflare Access identity
    // endpoint. The fetch fails, user stays null and protected routes bounce to /login
    // repeatedly (infinite-loop risk). Keep VITE_DEV_AUTH=true for local development only.
    if (import.meta.env.VITE_DEV_AUTH === 'true') {
      setUser({ email: 'dev@local' });
      setLoading(false);
      return undefined;
    }
    let off = false;
    (async () => {
      try {
        const res = await fetch('/cdn-cgi/access/get-identity');
        if (res.ok) {
          const d = await res.json();
          if (!off) setUser({ email: d.email || 'user' });
        }
      } catch (e) {
        if (!off) setUser(null);
      } finally {
        if (!off) setLoading(false);
      }
    })();
    return () => { off = true; };
  }, []);

  return <Ctx.Provider value={{ user, loading }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);
