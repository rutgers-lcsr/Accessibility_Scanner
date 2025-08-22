import { Content, Header } from "antd/es/layout/layout";

export default function Home() {

  return (
    <>
      <Header className="p-0">
        <h1>Home</h1>
        <p>Welcome to the accessibility audit tool.</p>
      </Header>
      <div>
        Hello
      </div>
      {/* <Content style={{ overflow: 'initial' }} className="mb-24 mx-4 initial">
        {Array.from({ length: 1000 }, (_, i) => (
          <div key={i} className="border-b border-gray-200 py-2">
            <h2 className="text-lg font-semibold">Report {i + 1}</h2>
            <p className="text-sm text-gray-500">Description for report {i + 1}</p>
          </div>
        ))}
      </Content> */}
    </>
  );
}
