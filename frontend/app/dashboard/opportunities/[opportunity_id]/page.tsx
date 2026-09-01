import { Metadata } from 'next';
import OpportunityClient from './ClientPage';

export const metadata: Metadata = {
  title: 'Discovery Pulse — Opportunity Detail',
};

export default function Page() {
  return <OpportunityClient />;
}
