import "./globals.css";
import NavTabs from './components/NavTabs';

export const metadata = {
  title: "Konduktor Dashboard",
  description: "Konduktor Dashboard V1",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <div className="flex-col">
          <NavTabs />
          <div>
            {children}
          </div>
        </div>
      </body>
    </html>
  );
}
