import { ZxcvbnFactory } from '@zxcvbn-ts/core'
import * as common from '@zxcvbn-ts/language-common'
import * as en from '@zxcvbn-ts/language-en'
import * as ro from '@zxcvbn-ts/language-ro'
const mk = (d) => new ZxcvbnFactory({ graphs: common.adjacencyGraphs, dictionary: { ...common.dictionary, ...d } })
const EN = mk(en.dictionary), ENRO = mk({ ...en.dictionary, ...ro.dictionary })
for (const pw of ['vacanta','Andrei1999!','TeIubescMult','VacantaLaMare1!','vacanță','vacanţă','teiubesc']) {
  const a=EN.check(pw), b=ENRO.check(pw)
  console.log(pw.padEnd(16),'EN',a.guesses.toExponential(1),'s'+a.score,'| EN+RO',b.guesses.toExponential(1),'s'+b.score, b.sequence.map(m=>m.token).join(' · '))
}
