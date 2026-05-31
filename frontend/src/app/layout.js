import "./globals.css";

export const metadata = {
  title: "LiveRisk — Financial Risk Intelligence",
  description: "Real-time portfolio risk analysis powered by Anakin Wire API",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-full">{children}</body>
    </html>
  );
}
