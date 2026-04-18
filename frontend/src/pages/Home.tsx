
import Hero from '../components/Hero';
import ExchangeRates from '../components/ExchangeRates';
import DigitalBanking from '../components/DigitalBanking';
import News from '../components/News';
import BranchLocator from '../components/BranchLocator';

const Home = () => {
  return (
    <main>
      <Hero />
      <News />
      <ExchangeRates />
      <DigitalBanking />
      <BranchLocator />
    </main>
  );
};

export default Home;
