import { GlobeLoader } from '../components/GlobeLoader'

/** Bare showcase of the loading indicator: 200×200, centred, off-white. */
export default function LoaderDemo() {
  return (
    <div className="fixed inset-0 z-40 grid place-items-center bg-canvas">
      <GlobeLoader size={200} />
    </div>
  )
}
