# Recall

Recall is a small web app for keeping track of team meeting notes. It picks out decisions, tasks, and questions for people to check. Later, teammates can ask what happened and open the meeting note behind the answer.

## Try the demo

Open `index.html` in a browser. No install or account is needed. The sample story follows three students making a class-notes app:

1. Click one of the example questions, or type your own, then open the meeting note linked under the answer.
2. Open the two meeting notes linked under the answer.
3. Visit **Meetings** to read the notes and check the saved items.
4. Add your own short meeting note. Review each suggested decision, task, or question before saving it.
5. Open **Connections** to see how notes, people, and decisions are related.
6. Run the six-question check to see which sample answers Recall finds.

The sample data and any notes you add are saved in this browser only.

## How it works

- HTML and CSS make the pages and forms.
- JavaScript finds sentences that look like decisions, tasks, and questions.
- A simple word match finds relevant saved items and their meeting notes.
- Browser storage keeps the demo data on the device.
- The connections view is drawn as an interactive SVG.

This version does not use an AI model, a server, or a company account. Its simple rules make it easy to see what it finds and where an answer came from. They also mean it can miss wording it was not designed to recognize.

## How this relates to the internship

- **HCI and prototyping:** people can check, edit, or remove suggestions. Answers link back to the original notes.
- **Knowledge graphs:** the connections view links decisions to people, topics, and meetings. It is a small in-browser graph, not a graph database.
- **Memory across meetings (the JD's memory theme):** meeting notes are saved as decisions, tasks, and questions, so people can find them later. The sample keeps the earlier decision when a plan changes.
- **Evaluation:** six sample questions check whether Recall finds the expected detail and its source. This is a demo check, not a user study.

## Product idea

- **Who might use it:** small teams that make plans in meetings and need to remember who agreed to do what.
- **What it is:** a web app. A chat app integration could be explored later, but this demo is not a bot.
- **Daily use:** after a meeting, add notes and check the suggestions. Before the next meeting, look up a decision or task.
- **How it might be sold:** a paid team plan is one idea to test with potential users; it has not been validated.

The sample scenario is a class project because it is easy to understand. The product idea is for teams at work too. A useful next study would compare this decision history with a plain meeting summary and ask people which helps them remember why a plan changed.

## Similar products and open question

[Fireflies AskFred](https://guide.fireflies.ai/articles/1512776728-global-askfred-get-answers-from-past-meetings-and-web-searches) offers questions across past meetings, while [Notion AI Meeting Notes](https://www.notion.com/help/ai-meeting-notes) captures meeting notes and action items. Finding and summarizing notes is already common. Recall's question to investigate is narrower: **does showing the old decision, the new decision, and the reason for the change help a team remember its choices?** The current demo shows that idea; it does not yet prove it works better.
