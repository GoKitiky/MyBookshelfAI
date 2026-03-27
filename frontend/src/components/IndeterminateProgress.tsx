import "./IndeterminateProgress.css";

type Props = {
  /** Exposed to assistive tech as the current long-running step. */
  statusText: string;
};

/**
 * Indeterminate busy indicator for long requests without per-item progress.
 */
export function IndeterminateProgress({ statusText }: Props) {
  return (
    <div
      className="indeterminate-progress"
      role="progressbar"
      aria-valuetext={statusText}
      aria-busy="true"
    >
      <div className="indeterminate-progress__track" aria-hidden>
        <div className="indeterminate-progress__fill" />
      </div>
    </div>
  );
}
