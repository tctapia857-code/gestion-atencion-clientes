interface LocalTicket {
  id: number;
  name: string;
  desk_id: number | null;
  status: 'waiting' | 'serving' | 'done';
  completed_at?: string;
}
interface LocalData { nextId: number; tickets: LocalTicket[]; }
const key = 'atencion-clientes-local-v1';

// Production runs entirely in the browser; development keeps the Flask API.
export async function localRequest(path: string, options?: RequestInit): Promise<Response> {
  const execute = () => {
    const saved = localStorage.getItem(key);
    const data: LocalData = saved ? JSON.parse(saved) : { nextId: 1, tickets: [] };
    const reply = (body: unknown, status = 200) => Response.json(body, { status });
    const fail = (error: string, status: number) => reply({ error }, status);
    const method = options?.method || 'GET';
    if (path === 'state' && method === 'GET') {
      return reply({
        waiting: data.tickets.filter(t => t.status === 'waiting'),
        desks: [1, 2, 3, 4].map(id => ({ id, ticket: data.tickets.find(t => t.status === 'serving' && t.desk_id === id) || null })),
        completed: data.tickets.filter(t => t.status === 'done').length,
        recent: data.tickets.filter(t => t.status === 'done').sort((a, b) => (b.completed_at || '').localeCompare(a.completed_at || '') || b.id - a.id).slice(0, 8)
      });
    }
    if (method !== 'POST') return fail('Ruta no encontrada.', 404);
    const body = JSON.parse(String(options?.body || '{}'));
    if (path === 'tickets') {
      const name = body?.name;
      if (typeof name !== 'string' || !name.trim() || name.trim().length > 80) return fail('Escribe un nombre de entre 1 y 80 caracteres.', 400);
      const ticket: LocalTicket = { id: data.nextId++, name: name.trim(), desk_id: null, status: 'waiting' };
      data.tickets.push(ticket);
      localStorage.setItem(key, JSON.stringify(data));
      return reply(ticket, 201);
    }
    const match = /^desks\/([1-4])\/(call|complete)$/.exec(path);
    if (!match) return fail('La mesa no existe.', 404);
    const desk = Number(match[1]);
    const active = data.tickets.find(t => t.status === 'serving' && t.desk_id === desk);
    if (match[2] === 'call') {
      if (active) return fail('Finaliza la atención actual antes de llamar otro turno.', 409);
      const ticket = data.tickets.find(t => t.status === 'waiting');
      if (!ticket) return fail('No hay clientes en espera.', 409);
      ticket.status = 'serving';
      ticket.desk_id = desk;
      localStorage.setItem(key, JSON.stringify(data));
      return reply({ message: 'Turno llamado.', ticket_id: ticket.id });
    }
    if (!Number.isInteger(body?.ticket_id)) return fail('Indica el turno que deseas finalizar.', 400);
    if (!active || active.id !== body.ticket_id) return fail('El turno cambió. Actualiza la pantalla e inténtalo de nuevo.', 409);
    active.status = 'done';
    active.completed_at = new Date().toISOString();
    localStorage.setItem(key, JSON.stringify(data));
    return reply({ message: 'Atención finalizada. Mesa disponible.' });
  };
  if (typeof navigator !== 'undefined' && navigator.locks) {
    return navigator.locks.request(key, execute);
  }
  return execute();
}
