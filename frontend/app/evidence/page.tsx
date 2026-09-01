import { Metadata } from 'next';
import EvidenceClient from './ClientPage';

export const metadata: Metadata = {
  title: 'Discovery Pulse — Evidence Explorer',
};

export default function Page() {
  return <EvidenceClient />;
}
