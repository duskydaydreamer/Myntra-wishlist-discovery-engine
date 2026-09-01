import { Metadata } from 'next';
import QueryClient from './ClientPage';

export const metadata: Metadata = {
  title: 'Discovery Pulse — Query Interface',
};

export default function Page() {
  return <QueryClient />;
}
