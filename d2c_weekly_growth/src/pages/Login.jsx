import { PROJECT } from '../utils/tabs';

export default function Login() {
  return (
    <div className="center-note">
      <h1>{PROJECT.name}</h1>
      <p>You need to sign in to view this dashboard. Access is managed by your administrator.</p>
      <button className="btn" onClick={() => window.location.assign('/')}>Try again</button>
    </div>
  );
}
