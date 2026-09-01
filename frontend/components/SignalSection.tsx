import DistributionBar from "./DistributionBar";
import WishlistBehaviorGroups from "./WishlistBehaviorGroups";
import { DistributionResponse } from "../lib/api";

interface SignalSectionProps {
  barriers: DistributionResponse | null; wishlistMotivations: DistributionResponse | null;
  purchaseIntents: DistributionResponse | null; uncertainties: DistributionResponse | null;
  informationNeeds: DistributionResponse | null; workarounds: DistributionResponse | null;
  journeyStages: DistributionResponse | null;
  decisionOutcomes: DistributionResponse | null;
}

export default function SignalSection(props: SignalSectionProps) {
  const primary = [
    ["What stops shoppers from buying", props.barriers, 6],
    ["What shoppers decided", props.decisionOutcomes, 6],
    ["Where friction happens", props.journeyStages, 6],
  ] as const;
  const secondary = [
    ["Likelihood to buy", props.purchaseIntents],
    ["What shoppers are unsure about", props.uncertainties],
    ["Information shoppers need", props.informationNeeds],
    ["How shoppers work around problems", props.workarounds],
  ] as const;

  return (
    <section className="mb-6" aria-labelledby="signal-heading">
      <div className="section-header">
        <div>
          <span className="eyebrow">Shopping signals</span>
          <h2 id="signal-heading" className="section-title">How shoppers move toward—or away from—purchase</h2>
          <p className="section-description">The clearest barriers, decisions, and moments in the shopping journey found in the customer evidence.</p>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {primary.map(([title, data, limit]) => data && <DistributionBar key={title} title={title} items={data.items} total={data.denominator} limit={limit} />)}
      </div>
      <details className="surface mt-4 overflow-hidden group">
        <summary className="flex min-h-[78px] cursor-pointer list-none items-center justify-between gap-5 px-5 py-4 marker:hidden sm:px-6">
          <div>
            <span className="eyebrow mb-1">Additional breakdowns</span>
            <h3 className="text-[15px] font-semibold text-[#25302c]">Explore more shopping signals</h3>
          </div>
          <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-[#edf2ef] text-[#60716a] transition-transform group-open:rotate-180" aria-hidden="true">
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7" className="h-4 w-4" strokeLinecap="round" strokeLinejoin="round"><path d="m6 8 4 4 4-4" /></svg>
          </span>
        </summary>
        <div className="space-y-4 border-t border-[#e1e6e3] bg-[#f8f9f7] p-4">
          {props.wishlistMotivations && <WishlistBehaviorGroups data={props.wishlistMotivations} />}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {secondary.map(([title, data]) => data && <DistributionBar key={title} title={title} items={data.items} total={data.denominator} unclassifiedCount={data.unclassified_count} limit={5} />)}
          </div>
        </div>
      </details>
    </section>
  );
}
