export enum GameStatus {
  SETUP = 'SETUP',
  PLAYING = 'PLAYING',
  FINISHED = 'FINISHED',
  EDITING_CAST = 'EDITING_CAST',
}

export interface Personality {
  id: string;
  name: string;
  prompt: string; // Empty for user type
  avatar: string; // Emoji
  type: 'ai' | 'user';
}

export interface StoryTurn {
  id: string;
  personality: Personality;
  text: string;
  type: 'bot' | 'summary';
}
