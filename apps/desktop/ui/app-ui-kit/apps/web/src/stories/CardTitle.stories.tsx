import type { Meta, StoryObj } from "@storybook/react-vite"
import { Card, CardHeader, CardTitle } from "@workspace/ui/components/card"

const meta = {
  title: "UI Kit/Components/CardTitle",
  component: CardTitle,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  args: { children: "Security overview" },
  argTypes: { children: { control: "text" } },
} satisfies Meta<typeof CardTitle>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  render: (args) => (
    <Card className="w-72 max-w-[90vw]">
      <CardHeader>
        <CardTitle {...args}>
          <h1>{args.children}</h1>
        </CardTitle>
      </CardHeader>
    </Card>
  ),
}

export const Small: Story = {
  render: (args) => (
    <Card size="sm" className="w-72 max-w-[90vw]">
      <CardHeader>
        <CardTitle {...args}>
          <h1>{args.children}</h1>
        </CardTitle>
      </CardHeader>
    </Card>
  ),
}
