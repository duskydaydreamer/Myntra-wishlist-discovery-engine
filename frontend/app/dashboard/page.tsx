import { Metadata } from 'next';
import DashboardClient from './ClientPage';

export const metadata: Metadata = {
  title: 'Discovery Pulse — Dashboard',
};

export default function Page() {
  return <DashboardClient />;
}
